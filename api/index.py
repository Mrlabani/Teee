from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from requests import Session
from http.cookiejar import MozillaCookieJar
from json import loads
from os import path
from re import findall
from typing import Dict, Any

app = Flask(__name__)

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']

def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'

@app.route('/terabox', methods=['GET'])
def terabox_download():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    if not path.isfile('cookies.txt'):
        return jsonify({'error': 'cookies.txt not found'}), 500
    try:
        jar = MozillaCookieJar('cookies.txt')
        jar.load()
        cookies = {cookie.name: cookie.value for cookie in jar}
    except Exception as e:
        return jsonify({'error': f"Cookie load error: {str(e)}"}), 500

    details = {'contents': [], 'title': '', 'total_size': 0}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    with Session() as session:
        try:
            response = session.get(url, headers=headers, cookies=cookies)
            if 'window.jsToken' not in response.text:
                return jsonify({'error': 'jsToken not found on page'}), 500
            jsToken = findall(r'window\.jsToken.*?%22(.*?)%22', response.text)[0]
            shortUrl = parse_qs(urlparse(response.url).query).get('surl', [None])[0]
            if not shortUrl:
                return jsonify({'error': 'surl not found'}), 500
            fileList = session.get(
                "https://www.1024tera.com/share/list",
                params={'app_id': '250528', 'jsToken': jsToken, 'shorturl': shortUrl},
                headers=headers,
                cookies=cookies
            ).json()
            if fileList.get("errno") != 0:
                return jsonify({'error': fileList.get("errmsg", "Fetch error")}), 500
            for content in fileList.get("list", []):
                size = content.get("size", 0)
                if isinstance(size, str) and size.isdigit():
                    size = float(size)
                details['total_size'] += size
                details['contents'].append({
                    'url': content['dlink'],
                    'filename': content['server_filename'],
                    'path': ''
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({
        'title': f"[{details['title']}]({url})",
        'total_size': get_readable_file_size(details['total_size']),
        'download_link': details['contents'][0]['url'] if details['contents'] else None
    })

# Vercel uses this:
def handler(environ, start_response):
    return app(environ, start_response)
  
