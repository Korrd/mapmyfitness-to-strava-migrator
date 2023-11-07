# Mapmyride to Strava migrator

## Motivation

I migrated to Strava after Endomondo got bought by Underarmour and it got replaced by multiple apps that offered lesser functionality. Since mapmyride does not offer a way to batch-export its workouts nor there were any tools to do so on the internet, I got tired of waiting and decided to code one of my own.

## Required parameters & preparation

### mmr-cookie

This is the mapMyRide session cookie from any browser request. It's a string on the "Cookie" header that will allow you to authenticate your request to mapMyRide. 

You can obtain it by opening any workout while looking at the network tab of the browser's inspector, and looking for it on the request section of the first request made by the browser.

It'll look like this:

```text
Cookie: undefined=US.[SOME_VALUE]; api-key=[SOME_API_KEY]; auth-token=[SOME_AUTH_TOKEN]; auth-token-expiry=[SOME_DATE]; runwebsessionid=[SOME_VALUE]
```

Our flag value is the part right of the `Cookie: ` bit.

### strava-access-token

This is a token that you must obtain from the Strava API APP created in order to programatically access Strava itself. 

You can get it as follows:

- [Creating a Strava API APP](https://developers.strava.com/docs/getting-started/#account) - Follow from step 2 on. This'll give you a read-only app. That's fine, as we'll get a write access app on the next step
- [Getting a Strava write token](https://yizeng.me/2017/01/11/get-a-strava-api-access-token-with-write-permission/) - This'll give you a write app. When adding the permission strings only add the `activity:write` permission, since there's an issue when creating a write token with more than one permission at a time.

### csv-file

This file contains a list of all activities within your mapmyride account. Obtain it by [following these instructions](https://support.mapmyfitness.com/hc/en-us/articles/1500009118782-Export-Workout-Data) and place it on the script's folder.

## How to use it

Invoke it as follows: 

```bash
python migrate-mapmyride-to-strava.py --csv_file=my_mmr_worklouts_file.csv --mmr_cookie="session cookie on a string" --strava-access-token="access token with activity:write permission"
```

Once the script is triggered, it'll request all of your workouts one by one as per the CSV file and download them to a folder called outputs.

Once downloaded, it'll upload them all to Strava as quickly as [Strava's API ratelimiter](https://developers.strava.com/docs/getting-started/#basic) will allow.
