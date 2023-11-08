import  csv, json, os, time, urllib.request, urllib3, zlib

def get_argument_value(args, flag, separator="="):
  """
  This function takes an argument list (args) and returns the value for a given flag in it,
  using the separator param to discern key from value. If not found, it'll return an empty string.
  """
  for element in args:
    if element.startswith(flag):
      return element.split(separator)[1]
  return ""  # Return empty if not found

def get_strava_access_token(client_id:str, client_secret:str, auth_code:str) -> str:
  """
  This function implements an oauth2 flow as per the strava API guide at https://developers.strava.com/docs/getting-started/#oauth.
  It'll take the client ID, client secret and auth code from the previous auth step and return the write token 
  required to upload activities. This is still a WIP.
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

def print_help_text(exit_code:int = 1):
  """
  This function prints the scripts' help text to stdout and exits with the exit code specified as its argument.
  """
  print("=" * 52)
  print("| Tool to migrate all mapmyride workouts to strava |".center(52))
  print("=" * 52)
  print(
      "\nUsage: migrate-mapmyride-to-strava.py --csv_file=my_mmr_worklouts_file.csv --mmr_cookie=\"session cookie on a string\" --strava-access-token=\"access token with activity:write permission\""
  )
  print("\nFlags:")
  print(
      "--mmr_cookie          | The session cookie from mapmyride. It can be stolen from any browser request to mapmyride via the inspector."
  )
  print(
      "--strava-access-token | Access token from strava API app. Must have activity:write permission. Follow these instructions to obtain it: https://yizeng.me/2017/01/11/get-a-strava-api-access-token-with-write-permission/"
  )
  print("--help              | Prints this help text")
  exit(exit_code)

def get_mmr_csv_file(headers:tuple, url: str, workdir: str) -> bool:
  """
  This function will get mapMyRide's workout list as a csv file and save it for use by the uploader.
  It'll return True if successful, False otherwise.
  Since headers are the same as for other mapMyRide request it'll take a headers tuple containing them all.
  It'll also take the script's workdir as well as the url endpoint to query for the csv file.
  """
  outputfile = f"{workdir}/workout_list.csv"
  # First, lets build our request, with stolen data from an actually working request from the 
  # mapMyRide website. Auth cookie as well.
  my_request = urllib.request.Request(url)

  for key, value in headers:
    my_request.add_header(key, value)

  # Now, let's download the workout. It'll be encoded as a gzip object
  try:
    page = urllib.request.urlopen(my_request).read().decode("utf-8")
    # Let's decode our gzip
    # Now, let's store our file onto disk
    outfile = open(outputfile,"w")
    outfile.write(str(page))
    outfile.close()
  except:
    return False, ""

  return True, outputfile

def list_mmr_workouts(csv_file: str) -> list:
  """
  This function reads the mapMyRide csv file (provided as a path via the csv_file param), and returns a list that will contain
  only those colums we'll be using. 
  """
  # From csv file analysis
  col_workout_type = 2
  col_notes = 12
  col_source = 13
  col_dl_link = 14
  payload = []
  # First, let's get info required to download a workout
  with open (csv_file, mode="r", newline="") as csvfile:
    item = csv.reader(csvfile, delimiter=",")
    for row in item:
      # This will skip the CSV file's header
      if "Date Submitted" in row:
        continue
      # Get download link
      link = row[col_dl_link]
      # Get notes + source (if they exist, otherwise empty string)
      notes = ((row[col_notes] if "b''" not in row[col_notes] else "")[2:-1] +
                (" (from " + 
                row[col_source] + "app)" if row[col_source] != "" else "")).strip()
      workout_type = row[col_workout_type]
      workout_id = row[col_dl_link].rsplit('/', 2)[1]

      payload.append([link, notes, workout_type, workout_id])
  return payload

def download_mmr_workouts(headers: tuple, workdir: str, outsubdir: str, workout_list: list) -> bool:
  """
  This function will take the headers, script's workdir, the outsubdir (name for a subdir to store files at the workdir),
  and the workout list from the list_mmr_workouts function, and use these to download ALL workouts from mapMyRide, saving
  each as an individual TCX file. It'll return True on success, False otherwise.
  """
  # Let's download each file from the payload list to a temp folder
  i = 0 # This'll be used to generate unique readable filenames

  for url, comments, wtype, id in workout_list:
    # Let's build our filename and check if it's already been saved. This'll allow some degree of resume capability
    filename = f"{'{0:0>4}'.format(str(i))}-{id}-{wtype.replace(' ','-').replace('/','')}.tcx"
    i = i + 1

    outputfile = f"{workdir}/{outsubdir}/{filename}"
    if not os.path.isfile(outputfile):
      # First, lets build our request, with stolen data from an actually working request from the 
      # mapMyRide website. Auth cookie as well.
      my_request = urllib.request.Request(str(url)
                                          .replace("/workout/","/workout/export/")
                                          .replace("http://", "https://")
                                          + "/tcx")

      for key, value in headers:
        my_request.add_header(key, value)

      # Now, let's download the workout. It'll be encoded as a gzip object
      try:
        page = urllib.request.urlopen(my_request).read()
        # Let's decode our gzip
        decoded_result = zlib.decompress(page, 16 + zlib.MAX_WBITS).decode("utf-8")
        # Now, let's store our file onto disk
        print(f"💾 Exporting file \"{filename}\" from workout at \"{url}\"...")
        outfile = open(outputfile,"w")
        outfile.write(str(decoded_result))
        outfile.close()
      except:
        return False
    else:
      print(f"✅ Skipping file \"{filename}\", as it already exists...")
      continue

  print(f"\n🏁 Workouts downloaded. \"{i}\" workout{'s' if i > 1 else ''} to \"{workdir}/{outsubdir}\"\n")
  return True

def upload_workouts_to_strava(tcx_files_dir: str, workout_list: list, strava_access_token: str) -> bool:
  """
  This function takes the tcx files dir, the workout list from the list_mmr_workouts function, and the strava write access token,
  and uploads all TCX files that match the workout_list items by workout ID to Strava. It'll return True on success, False otherwise.
  """
  throttle_wait = 910 # Sleep for 15 minutes before resuming, to avoid 
                      # hitting API ratelimiter

  # ===============================================================================================
  # First, let's construct a list of files to upload ==============================================
  # ===============================================================================================
  filelist = os.listdir(tcx_files_dir)

  result = {}
  for list_element in filelist:
    if ".tcx" not in list_element: # Filter out other files, like .gitignore, .DS_Store, etc
      continue
    result[list_element.split('-')[1]] = list_element # Add to dict, use workout id as key

  full_list=[]
  for list_item in workout_list:
    if list_item[3] in result:
      full_list.append(list_item + [result[list_item[3]]])
  full_list.sort(reverse=True)
  # ===============================================================================================
  # Now, let's upload our files one by one ========================================================
  # ===============================================================================================
  # Getting strava's auth code
  http = urllib3.PoolManager()
  
  for link, notes, workout_type, workout_id, workout_file in full_list:
    with open(tcx_files_dir + "/" + workout_file, 'rb') as file:
      tcx_data = file.read()

    # Create the request headers
    headers = {
      'Authorization': f'Bearer {strava_access_token}',
      'Content-Disposition': f'attachment; filename="{workout_file}"'
    }
    
    # create the data payload
    data = {
      "data_type": "tcx",
      'file': (tcx_files_dir + "/" + workout_file, tcx_data, 'application/tcx'),
      'description': notes
    }
    
    # Send the request
    try:
      response = http.request(
        method='POST',
        url='https://www.strava.com/api/v3/uploads',
        headers=headers,
        fields=data
      )
    except:
      return False

    # Print the response
    response_status_code = response.headers._container['status'][1][0:3]

    # [15min-limit, daily-limit]
    response_x_ratelimit_limit = response.headers._container['x-ratelimit-limit'][1].split(",")
    # [15min-limit-usage, daily-limit-usage]
    response_x_ratelimit_usage = response.headers._container['x-ratelimit-usage'][1].split(",")

    if response_status_code == '201': # Success!
      print(f"✅ Workout \"{workout_file}\" uploaded successfully. \
            15m ratelimit [used/limit]: [{response_x_ratelimit_usage[0]},{response_x_ratelimit_limit[0]}] \
            daily ratelimit [used/limit]: [{response_x_ratelimit_usage[1]},{response_x_ratelimit_limit[1]}]")
      os.rename(f"{tcx_files_dir}/{workout_file}",f"{tcx_files_dir}/archive/{workout_file}")
    elif response_status_code == '429': # Hit ratelimiter
      print(f"\n⏰ Workout \"{workout_file}\" hit a ratelimit. Waiting {throttle_wait / 60} minutes before retrying\n")
      time.sleep(throttle_wait)
    elif response_status_code == '500': # Server error
      print(f"❌ Workout \"{workout_file}\" failed to upload due to error 500. Left in place so it can be retried")
      return False

    if int(response_x_ratelimit_usage[0]) >= int(response_x_ratelimit_limit[0]): # Hit 15-min ratelimit
      print(f"\n⏰ 15-min ratelimit reached. Waiting {throttle_wait / 60} minutes before retrying\n")
      time.sleep(throttle_wait)

    if int(response_x_ratelimit_usage[1]) >= int(response_x_ratelimit_limit[1]): # Hit daily ratelimit
      print(f"\n💥 Daily ratelimit reached. Wait until tomorrow and try again.")
      return False
  return True  
