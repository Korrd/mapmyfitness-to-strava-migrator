"""
This module contains all functions used by this program, for greater code clarity.

  - `download_mmr_workouts()`: downloads workouts from mapmyride
  - `get_mmr_csv_file()`: gets a list of all workouts as a csv file
  - `get_strava_access_token()`: `WIP`: gets strava's write access token. Part of the not yet implemented oauth2 auth flow
  - `list_mmr_workouts()`: builds a list of mapmyride workouts with only the data we need
  - `print_help_text()`: prints this program's help text and quits
  - `upload_workouts_to_strava()`: uploads all workouts to strava from TCX files

For more details onto each function, these are also docstring'd.
"""
import  csv, os, time, urllib.request, urllib3, zlib

def get_argument_value(args:list[str], flag:str, separator:str = "=") -> str:
  """
  #### Description
  A key-value search that will search a list and return the value of a given flag, or an empty string if not found.

  #### Parameters
    - `args`: list of arguments from the command line, each element in a --key=value format but the first one which is the file's path
    - `flag`: '--key' to search its 'value' for
    - `separator`: argument separator. An '=' sign by default

  #### Returns
    - The `flag's value` if found. Otherwise an `empty string`

  #### Notes
  If your value also contains instances of the separator itself as a part of it, set the separator as --flag+separator: i.e '--flag='
  """
  for element in args:
    if element.startswith(flag):
      return element.split(separator)[1]
  return "" # Return empty if not found

def print_help_text(exit_code:int = 1):
  """
  #### Description
  Prints this program's help text `and quits` with the provided exit code.

  #### Parameters
    - `exit_code`: The exit code we want to exit with
  """
  print("=" * 52)
  print("| Tool to migrate all mapmyride workouts to strava |".center(52))
  print("=" * 52)
  print(
      "\nUsage: migrate-mapmyride-to-strava.py --mmr_cookie=\"session cookie on a string\""
  )
  print("\nFlags:")
  print(
      "--mmr_cookie          | The session cookie from mapmyride. It can be stolen from any browser request to mapmyride via the inspector."
  )
  print("--help              | Prints this help text")
  exit(exit_code)

def get_mmr_csv_file(headers:tuple, workdir: str, url: str = "https://www.mapmyfitness.com/workout/export/csv") -> bool:
  """
  #### Description
  Gets mapMyRide's workout list as a csv file and saves it for use by the uploader.

  #### Parameters
    - `headers`: A tuple containing the headers required for this request
    - `url`: Endpoint where to download the CSV file data from. Defaults to currently known value but can be overriden
    - `workdir`: Working directory where to store the CSV file at

  #### Returns
    - `True` if successful, `False` if not.

  #### Notes
  This function and how to retrieve the csv file programatically were derived from its [CSV documentation](https://support.mapmyfitness.com/hc/en-us/articles/1500009118782-Export-Workout-Data) & by some req-res hacking, since applications for API access are no longer being granted.
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

def list_mmr_workouts(csv_file_path: str) -> list:
  """
  #### Description
  Reads the mapMyRide csv file and returns a list that only contains those colums we'll be using.
  #### Parameters
    - `csv_file_path`: Full path to the csv_file to be read

  #### Returns
    - A `list` containing only those items that'll be used by this program

  #### Notes
  This one comes from analyzing mapMyRide's CSV file, since it's not documented anywhere and they're no longer granting requests for API access.
  """
  # From csv file analysis
  col_workout_type = 2
  col_notes = 12
  col_source = 13
  col_dl_link = 14
  payload = []
  # First, let's get info required to download a workout
  with open (csv_file_path, mode="r", newline="") as csvfile:
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

def download_mmr_workouts(headers: tuple, output_dir: str, workout_list: list) -> bool:
  """
  #### Description
  Downloads all workouts, each as a TCX file, from a mapmyride account onto a chosen directory.

  #### Parameters
    - `headers`: A tuple containing the headers required for this request
    - `output_dir`: Target directory where to store the workouts at
    - `workout_list`: The list generated by the `list_mmr_workouts()` function

  #### Returns
    - `True` if successful, `False` if not

  #### Notes
  This function may take a while to run if the targeted mapmyride account holds too many workouts. Since there's no public-facing API documentation available, it's unknown if a ratelimiter is implemented on their side.
  """
  # Let's download each file from the payload list to a temp folder
  i = 0 # This'll be used to generate unique readable filenames

  for url, comments, wtype, id in workout_list:
    # Let's build our filename and check if it's already been saved. This'll allow some degree of resume capability
    filename = f"{'{0:0>4}'.format(str(i))}-{id}-{wtype.replace(' ','-').replace('/','')}.tcx"
    i = i + 1

    outputfile = f"{output_dir}/{filename}"
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

  print(f"\n🏁 Workouts downloaded. \"{i}\" workout{'s' if i > 1 else ''} to \"{output_dir}\"\n")
  return True

def upload_workouts_to_strava(workouts_dir: str, workout_list: list, strava_access_token: str) -> bool:
  """
  #### Description
  Uploads all workouts found on a given directory that match the mapmyride CSV file to Strava.

  #### Parameters
    - `workouts_dir`: The full path to the directory where all the TCX files reside
    - `workout_list`: The list generated by the `list_mmr_workouts()` function
    - `strava_access_token`: The strava access token provided to this program

  #### Returns
    - `True` if successful, `False` if not

  #### Notes
  This function may take a while to run if there are too many workouts, since Strava implements [a ratelimiter on its API](https://developers.strava.com/docs/getting-started/#basic).
  """
  throttle_wait = 910 # Sleep for 15 minutes before resuming, to avoid
                      # hitting API ratelimiter

  # ===============================================================================================
  # First, let's construct a list of files to upload ==============================================
  # ===============================================================================================
  filelist = os.listdir(workouts_dir)

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

  for _, notes, _, _, workout_file in full_list:
    with open(workouts_dir + "/" + workout_file, 'rb') as file:
      tcx_data = file.read()

    # Create the request headers
    headers = {
      'Authorization': f'Bearer {strava_access_token}',
      'Content-Disposition': f'attachment; filename="{workout_file}"'
    }

    # create the data payload
    data = {
      "data_type": "tcx",
      'file': (workouts_dir + "/" + workout_file, tcx_data, 'application/tcx'),
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
      os.rename(f"{workouts_dir}/{workout_file}",f"{workouts_dir}/archive/{workout_file}")

    elif response_status_code == '429': # Hit ratelimiter
      print(f"\n⏰ Workout \"{workout_file}\" hit a ratelimit. Waiting {throttle_wait / 60} minutes before retrying\n")
      time.sleep(throttle_wait)

    elif response_status_code == '500': # Server error
      print(f"❌ Workout \"{workout_file}\" failed to upload due to error 500. Left in place so it can be retried")

    if int(response_x_ratelimit_usage[0]) >= int(response_x_ratelimit_limit[0]): # Hit 15-min ratelimit
      print(f"\n⏰ 15-min ratelimit reached. Waiting {throttle_wait / 60} minutes before retrying\n")
      time.sleep(throttle_wait)

    if int(response_x_ratelimit_usage[1]) >= int(response_x_ratelimit_limit[1]): # Hit daily ratelimit
      print(f"\n💥 Daily ratelimit reached. Wait until tomorrow and try again.")
      return False
  return True
