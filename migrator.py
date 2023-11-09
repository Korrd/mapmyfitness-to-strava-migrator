
# TODO - Nice to have: automatic oauth2 auth flow

import os
from sys import argv as args
import helpers as f

def main(args):

  result:bool = False

  # Let's get our flags...
  FLAG_HELP = "--help" in args
  if FLAG_HELP:
    f.print_help_text(2)

  # Get args
  workdir = os.path.dirname(os.path.realpath(__file__))
  mmr_cookie = f.get_argument_value(args=args, flag="--mmr-cookie", separator="--mmr-cookie=")
  strava_access_token = f.get_argument_value(args=args, flag="--strava-access-token", separator="--strava-access-token=")
  
  if mmr_cookie == "":
    print("❌ Argument \"--mmr-cookie\" is missing or empty!")
    f.print_help_text(1)

  if strava_access_token == "":
    print("❌ Argument \"--strava-access-token\" is missing or empty!")
    f.print_help_text(1)

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

  result, csv_file = f.get_mmr_csv_file(headers=mmr_headers, url=csv_url, workdir=workdir)
  if result:
    print("✅ CSV File downloaded.\n")
  else:
    print("❌ Failed to Obtain CSV file.")
    exit(1)

  workout_list = f.list_mmr_workouts(csv_file_path=csv_file)

  result = f.download_mmr_workouts(headers=mmr_headers, output_dir=f"{workdir}/{files_dir}",
                        workout_list=workout_list
                        )

  if not result:
    print("❌ Failed to obtain mapMyRide workouts.")
    exit(1)
  else:
    print("\n✅ Workouts downloaded. Uploading to Strava...\n")

  result = f.upload_workouts_to_strava(workouts_dir=f"{workdir}/{files_dir}",
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
