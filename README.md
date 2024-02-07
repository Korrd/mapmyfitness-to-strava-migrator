# Mapmyride to Strava migrator

![linting badge](https://github.com/korrd/mapmyfitness-to-strava-migrator/actions/workflows/pylint.yml/badge.svg)

## Motivation

I migrated to Strava after Endomondo got bought by Underarmour and it got replaced by multiple apps that offered lesser functionality. Since Mapmyride does not offer a way to batch-export its workouts nor there were any tools to do so on the internet, I got tired of waiting and decided to code one of my own.

## Prerequisites

If needed, install all required packages described on the `requirements.txt` file using pip as follows:

```bash
make setup
```

## Required parameters & preparation

### mmr-cookie

This is the mapMyRide session cookie from any browser request. It's a string on the "Cookie" header that will allow you to authenticate your request to mapMyRide.

You can obtain it by opening any workout while looking at the network tab of the browser's inspector, and looking for it on the request section of the first request made by the browser.

It'll look like this:

```s
Cookie: undefined=US.[SOME_VALUE]; api-key=[SOME_API_KEY]; auth-token=[SOME_AUTH_TOKEN]; auth-token-expiry=[SOME_DATE]; runwebsessionid=[SOME_VALUE]
```

Our flag value is the part right of the `Cookie: ` bit.

## How to use it

- Get the `Client ID` & `Secret` values from strava's at its [API config page](https://www.strava.com/settings/api). If no API app is set, you can create a new one [following these instructions](https://developers.strava.com/docs/getting-started/#account)

- Just run the tool from `run.py`, providing `Client ID` and `Secret` when asked, then wait for it:

  ```bash
  python migrator.py --mmr_cookie="<session cookie on a string>"
  ```

Once the script is triggered, it'll request all of your workouts one by one as per the CSV file and download them to a folder called outputs.

Once downloaded, it'll upload them all to Strava as quickly as the [Strava's API ratelimiter](https://developers.strava.com/docs/getting-started/#basic) allows.
