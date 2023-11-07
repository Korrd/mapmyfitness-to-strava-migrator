
# TODO - Nice to have: automatic oauth2 auth flow

import csv, os, urllib.request, zlib, time, urllib3
from sys import argv as args

#region functions
def get_argument_value(args, flag, separator="="):
  for element in args:
    if element.startswith(flag):
      return element.split(separator)[1]
  return ""  # Return empty if not found

def print_help_text():
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
  
def get_mmr_csv_file(headers:tuple, url: str, workdir: str) -> bool:
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

def upload_workouts_to_strava(workdir: str, workout_list: list, strava_access_token: str) -> bool:
  throttle_wait = 910 # Sleep for 15 minutes before resuming, to avoid 
                      # hitting API ratelimiter

  # ===============================================================================================
  # First, let's construct a list of files to upload ==============================================
  # ===============================================================================================
  filelist = os.listdir(workdir)

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
    with open(workdir + "/" + workout_file, 'rb') as file:
      tcx_data = file.read()

    # Create the request headers
    headers = {
      'Authorization': f'Bearer {strava_access_token}',
      'Content-Disposition': f'attachment; filename="{workout_file}"'
    }
    
    # create the data payload
    data = {
      "data_type": "tcx",
      'file': (workdir + "/" + workout_file, tcx_data, 'application/tcx'),
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
      print(f"✅ Workout \"{workout_file}\" uploaded successfully. 15m ratelimit [used/limit]: [{response_x_ratelimit_usage[0]},{response_x_ratelimit_limit[0]}] daily ratelimit [used/limit]: [{response_x_ratelimit_usage[1]},{response_x_ratelimit_limit[1]}]")
      os.rename(f"{workdir}/{workout_file}",f"{workdir}/archive/{workout_file}")
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
#endregion

def main(args):

  result:bool = False

  # Let's get our flags...
  FLAG_HELP = "--help" in args
  if FLAG_HELP:
    print_help_text()
    exit(2)

  # Get args
  workdir = os.path.dirname(os.path.realpath(__file__))
  mmr_cookie = get_argument_value(args=args, flag="--mmr-cookie", separator="--mmr-cookie=")
  strava_access_token = get_argument_value(args=args, flag="--strava-access-token", separator="--strava-access-token=")
  
  if mmr_cookie == "":
    print("❌ Argument \"--mmr-cookie\" is missing or empty!")
    print_help_text()
    exit(1)
  if strava_access_token == "":
    print("❌ Argument \"--strava-access-token\" is missing or empty!")
    print_help_text()
    exit(1)

  csv_url = "https://www.mapmyfitness.com/workout/export/csv"
  files_dir = "outputs"
  mmr_headers = (
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),
    ("Accept-Encoding","gzip, deflate, br"),
    ("Accept-Language","en-GB,en;q=0.5"),
    ("Connection","keep-alive"),
    ("Cookie", mmr_cookie),
    ("DNT","1"),
    ("Host","www.mapmyfitness.com"),
    ("Sec-Fetch-Dest","document"),
    ("Sec-Fetch-Mode","navigate"),
    ("Sec-Fetch-Site","none"),
    ("Sec-Fetch-User","?1"),
    ("Sec-GPC","1"),
    ("TE","trailers"),
    ("Upgrade-Insecure-Requests","1"),
    ("User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0")
  )

  result, csv_file = get_mmr_csv_file(headers=mmr_headers, url=csv_url, workdir=workdir)
  if result:
    print("✅ CSV File downloaded.\n")
  else:
    print("❌ Failed to Obtain CSV file.")
    exit(1)

  workout_list = list_mmr_workouts(csv_file)

  result = download_mmr_workouts(headers=mmr_headers, workdir=workdir,
                        outsubdir=files_dir,
                        workout_list=workout_list,
                        )

  if not result:
    print("❌ Failed to obtain mapMyRide workouts.")
    exit(1)
  else:
    print("\n✅ Workouts downloaded. Uploading to Strava...\n")

  result = upload_workouts_to_strava(workdir=f"{workdir}/{files_dir}",
                            workout_list=workout_list,
                            strava_access_token=strava_access_token
                            )
  if result:
    print("✅ Done. Workouts uploaded.")
    exit(0)
  else:
    print("❌ Failed to upload workouts to Strava.")
    exit(1)

if __name__ == "__main__":
  main(args)
