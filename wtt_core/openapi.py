import re
import json
import subprocess
from urllib.parse import urlparse, urljoin
import requests

class OpenAPIParser:
    """Handles OpenAPI / Swagger UI specs extraction & endpoint matching."""

    @staticmethod
    def is_swagger_url(url: str, html_content: str = "") -> bool:
        lower_url = url.lower()
        if any(k in lower_url for k in ['swagger', 'openapi', 'api-docs', 'redoc']):
            return True
        if html_content:
            lower_html = html_content.lower()
            if any(k in lower_html for k in ['swagger-ui', 'swaggerui', 'swaggerdoc', 'openapi']):
                return True
        return False

    @classmethod
    def extract_spec(cls, url: str, session: requests.Session) -> tuple[dict | None, str | None]:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        init_js_candidates = [
            urljoin(url, "swagger-ui-init.js"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "swagger-ui-init.js"),
            f"{base_url}/swagger-docs/swagger-ui-init.js",
            f"{base_url}/api-docs/swagger-ui-init.js"
        ]

        for init_url in set(init_js_candidates):
            try:
                r = session.get(init_url, timeout=8)
                if r.status_code == 200 and "swaggerDoc" in r.text:
                    spec = cls._parse_swagger_init_js(r.text)
                    if spec:
                        return spec, init_url
            except Exception:
                pass

        try:
            r = session.get(url, timeout=8)
            if r.status_code == 200:
                html = r.text

                spec_url_match = re.search(r'url\s*:\s*["\']([^"\']+\.json[^"\']*)["\']', html, re.I)
                if spec_url_match:
                    target = urljoin(url, spec_url_match.group(1))
                    spec = cls._fetch_json(target, session)
                    if spec:
                        return spec, target

                if "swagger-ui-init.js" in html:
                    init_target = urljoin(url, "swagger-ui-init.js")
                    r_init = session.get(init_target, timeout=8)
                    if r_init.status_code == 200:
                        spec = cls._parse_swagger_init_js(r_init.text)
                        if spec:
                            return spec, init_target
        except Exception:
            pass

        probes = [
            urljoin(url, "swagger.json"),
            urljoin(url, "openapi.json"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "swagger.json"),
            urljoin(base_url + parsed.path.rstrip('/') + '/', "openapi.json"),
            f"{base_url}/swagger.json",
            f"{base_url}/openapi.json",
            f"{base_url}/v3/api-docs",
            f"{base_url}/api-docs",
            f"{base_url}/swagger/v1/swagger.json"
        ]

        for probe_url in probes:
            spec = cls._fetch_json(probe_url, session)
            if spec and ("openapi" in spec or "swagger" in spec or "paths" in spec):
                return spec, probe_url

        return None, None

    @staticmethod
    def _fetch_json(url: str, session: requests.Session) -> dict | None:
        try:
            r = session.get(url, timeout=6)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_swagger_init_js(js_text: str) -> dict | None:
        modified_text = js_text.replace('var options =', 'globalThis.options =', 1)
        mock_env = '''
        const SwaggerUIBundle = function(opts) { return {}; };
        SwaggerUIBundle.presets = { apis: {} };
        SwaggerUIBundle.plugins = { DownloadUrl: {} };
        const SwaggerUIStandalonePreset = {};
        const window = { location: { search: '', origin: '' } };
        '''
        js_code = mock_env + modified_text + '\nif (typeof window.onload === "function") window.onload(); console.log(JSON.stringify(globalThis.options ? globalThis.options.swaggerDoc : null));'
        try:
            res = subprocess.run(['node'], input=js_code, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                out = res.stdout.strip()
                if out != "null":
                    return json.loads(out)
        except Exception:
            pass
        return None

    @classmethod
    def match_fragment(cls, spec: dict, fragment: str) -> dict | None:
        if not fragment:
            return None

        clean_frag = fragment.lstrip('#/').rstrip('/')
        parts = [p for p in clean_frag.split('/') if p]
        if not parts:
            return None

        tag = parts[0] if len(parts) > 1 else None
        op_str = parts[-1]

        methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']
        matched_method = None
        calc_path = None

        for m in methods:
            if op_str.lower().startswith(m + '_'):
                matched_method = m
                raw_path_part = op_str[len(m)+1:]
                calc_path = '/' + raw_path_part.replace('_', '/')
                break

        paths = spec.get('paths', {})

        if calc_path and matched_method:
            for p, methods_dict in paths.items():
                if p.lower() == calc_path.lower() and matched_method in methods_dict:
                    return {
                        'path': p,
                        'method': matched_method.upper(),
                        'details': methods_dict[matched_method],
                        'tag': tag
                    }

        for p, methods_dict in paths.items():
            for m, details in methods_dict.items():
                op_id = details.get('operationId', '')
                if op_id and op_id.lower() == op_str.lower():
                    return {
                        'path': p,
                        'method': m.upper(),
                        'details': details,
                        'tag': tag
                    }

        for p, methods_dict in paths.items():
            for m, details in methods_dict.items():
                if matched_method and m.lower() != matched_method.lower():
                    continue
                if all(word in p for word in op_str.split('_') if len(word) > 2 and word not in ['api', 'v1', 'v2', 'post', 'get', 'put']):
                    return {
                        'path': p,
                        'method': m.upper(),
                        'details': details,
                        'tag': tag
                    }

        return None
