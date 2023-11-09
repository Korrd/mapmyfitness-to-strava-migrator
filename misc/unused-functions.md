# Unused functions

Oauth2 authorization flow was meant to be implemented on this script, but I've since then decided not to do so. This file contains some code I had worked on to make it so just in case I change my mind.


## Getting Strava write token

```python
import json
def get_strava_access_token(client_id:str, client_secret:str, auth_code:str) -> str:
  """
  #### Description
  Implements part of an oauth2 authorization flow as per the strava API guide at https://developers.strava.com/docs/getting-started/#oauth.
  
  #### Parameters
    - `client_id`: The client ID from the strava API app
    - `client_secret`: The client secret from the strava API app
    - `auth_code`: A code returned as part of the previous authorization bit, which is single-use
  
  #### Returns
    - The `strava access token`, with whatever permissions were set during the previous oauth2 step

  #### Notes
  This function is part of an oauth2 authorization flow. It does not yet handle the previous step which actually authorizes access, but rather the token bits. `Hence, this is still a work in progress`, not intended yet for use.
  """
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
```
