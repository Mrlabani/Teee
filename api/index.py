from flask import Flask, request, jsonify
from requests import Session
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlparse, parse_qs
from re import findall
from os import path

app = Flask(__name__)

@app.route("/terabox", methods=["GET"])
def terabox():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    cookie_path = path.join(path.dirname(__file__), "cookies.txt")
    if not path.isfile(cookie_path):
        return jsonify({"error": "cookies.txt not found"}), 500

    jar = MozillaCookieJar(cookie_path)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
        cookies = {cookie.name: cookie.value for cookie in jar}
    except Exception as e:
        return jsonify({"error": f"Cookie load error: {e}"}), 500

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        with Session() as s:
            res = s.get(url, headers=headers, cookies=cookies)
            jsToken = findall(r'window\.jsToken.*?%22(.*?)%22', res.text)[0]
            shortUrl = parse_qs(urlparse(res.url).query).get("surl", [None])[0]
            if not shortUrl:
                return jsonify({"error": "Short URL not found"}), 500

            params = {
                "app_id": "250528",
                "jsToken": jsToken,
                "shorturl": shortUrl
            }
            res2 = s.get("https://www.1024tera.com/share/list", params=params, headers=headers, cookies=cookies).json()
            if res2.get("errno") != 0:
                return jsonify({"error": res2.get("errmsg", "Unknown error")}), 500

            file = res2["list"][0]
            return jsonify({
                "filename": file["server_filename"],
                "download_url": file["dlink"]
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def handler(environ, start_response):
    return app(environ, start_response)
    
