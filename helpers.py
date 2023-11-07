# Unused code from the migrator app
import urllib3, json

def get_strava_access_token(client_id:str, client_secret:str, auth_code:str) -> str:
  http = urllib3.PoolManager()
  
  grant_type = 'authorization_code'
  
  urlToken = 'https://www.strava.com/api/v3/oauth/token'
  headers = {
    'Content-Type': 'application/json'
  }
  body = {
    'client_id': client_id,
    'client_secret': client_secret,
    'code': auth_code,
    'grant_type': grant_type
  }
  
  response = http.request('POST', urlToken, headers=headers, body=json.dumps(body).encode('utf-8'))
  response_data = json.loads(response.data.decode('utf-8'))
  strava_access_token = response_data['access_token']
  return strava_access_token
