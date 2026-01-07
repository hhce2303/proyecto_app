from urllib.request import Request, urlopen
import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def cargar_healthcheck_por_requesters_multiples(request_id):
    """
    Hace múltiples requests (uno por requester) y combina los resultados.
    Fallback cuando la API no soporta criteria múltiples.
    """
    url = f"https://sigdomain01:8080/api/v3/requests{request_id}"
    headers = {
        "authtoken": "FE76F794-9884-4C06-85CC-A641E2B20726",
        "Accept": "application/json",
        "Content-Type" : "application/x-www-form-urlencoded"
    }
    httprequest = Request(url, headers=headers)
    try:
        with urlopen(httprequest) as response:
            print(response.read().decode())
    except requests.HTTPError as e:
        print(e.read().decode())



if __name__ == "__main__":
    cargar_healthcheck_por_requesters_multiples("/145159")