
# TODO - Nice to have: automatic oauth2 auth flow

import os
from sys import argv as args
import helpers as f
from strava_oauth import strava_oauth as oauth

def main(args):
  result = False

  # Let's get our flags...
  FLAG_HELP = "--help" in args
  if FLAG_HELP:
    f.print_help_text(2)

  # Get args
  mmr_cookie = f.get_argument_value(args=args, flag="--mmr-cookie", separator="--mmr-cookie=")

  if mmr_cookie == "":
    print("❌ Argument \"--mmr-cookie\" is missing or empty!")
    f.print_help_text(1)

  #region #? Do strava auth
  workdir = os.path.dirname(os.path.realpath(__file__))
  secrets_file = f"{workdir}/temp/secrets.json"
  strava_access_token, refresh_token = "", ""

  if not os.path.exists(secrets_file):
    # There's no secrets file. Ask user for client ID & Secret
    client_id, client_secret = oauth.ask_for_secrets()
    if client_secret == "" or client_id == "":
      print("[strava] \033[91m❌ Either the \"Client Secret\" or \"ID\" provided are empty. Check them then try again.\033[0m")
      exit(1)
    else:
      # Write client info to secrets file
      oauth.write_secrets_file(secrets_file=secrets_file, \
                              client_id=client_id, \
                              client_secret=client_secret)
  else:
    # Get all credentials from file
    strava_access_token, refresh_token, client_id, client_secret = oauth.read_secrets_file(secrets_file)

  if strava_access_token == "":
    # No access token present. Let's retrieve them
    strava_access_token, refresh_token = oauth.do_oauth_flow(client_id=client_id, \
                                                      client_secret=client_secret)
  else:
    if not oauth.check_access_token(strava_access_token):
      # Refresh invalid access_token since it's invalid, so we don't bother user
      strava_access_token = oauth.refresh_access_token(client_id=client_id, \
                                                client_secret=client_secret, \
                                                refresh_token=refresh_token)

  if strava_access_token == "":
    # If at this point we still have no access token, we've failed and can't do anything about it,
    # so we exit with error
    print("[strava] \033[91m❌ Unable to retrieve tokens. Check provided \"Client ID\" & \"Secret\", then try again\033[0m")
    exit(1)
  else:
    oauth.write_secrets_file(secrets_file=secrets_file, \
                            client_id=client_id, \
                            client_secret=client_secret, \
                            access_token=strava_access_token, \
                            refresh_token=refresh_token)

  print("[strava] \033[92m🔐 Authentication successful!\n\033[0m")
  #endregion

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
