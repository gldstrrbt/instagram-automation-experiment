# Instagram Automation Experiment

Historical Python browser-automation experiment using `nodriver` and BeautifulSoup to inspect Instagram pages, explore-feed posts, follow controls, and related DOM structures.

This is preserved as an archival prototype rather than a maintained automation tool. Instagram's DOM and access controls change frequently, so selectors and flows may no longer work as written.

## Security note

The recovered source contained an embedded Discord webhook and a commented login credential. Those values were removed before publication. Optional webhook alerts now read `DISCORD_WEBHOOK_URL` from the environment.

## Dependencies

The experiment imports `nodriver`, `requests`, `pyautogui`, `pywin32`, `pytz`, `PyYAML`, `python-dateutil`, and `beautifulsoup4`.
