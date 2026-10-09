<!-- README.md -->

# ABCKASEFI

ABeCedni KAtalog SErialu a FIlmu - a Kodi add-on that browses movies and series alphabetically and hands playback over to Nokturno.

<div align="center">

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekd) [!["PayPal.me"](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?business=LJ5ZF7Q9KMTRW&no_recurring=0&currency_code=USD)

</div>

## What it is

ABCKASEFI is a video add-on for Kodi 20 and newer. It lists movies and series by letter (A-Z and 0-9), by TMDB lists (top rated, popular, trending) and by search, with Czech, Slovak or English titles. The list data comes from a small catalog service that you run yourself. When you pick a movie or an episode, the add-on passes it to the Nokturno add-on, which does the playback.

The add-on hosts, indexes and distributes no content. It only shows titles from your own catalog service.

## Requirements

- Kodi 20 (Nexus) or newer.
- The [Nokturno](https://github.com/mirecekd/plugin.video.nokturno) add-on, installed and set up separately.
- The abckasefi-catalog service ([github.com/mirecekd/abckasefi-catalog](https://github.com/mirecekd/abckasefi-catalog)), reachable from the device that runs Kodi, with its address and API token.
- Optional: `script.module.certifi`, used as the CA bundle for HTTPS when it is installed.

## Installation

Install through the Kodi repository so that updates arrive automatically:

1. Download the repository zip from <https://mirecekd.github.io/plugin.video.abckasefi/repository.abckasefi/repository.abckasefi.zip>.
2. In Kodi open Settings, Add-ons, Install from zip file, and select the downloaded file.
3. Open Install from repository, choose the ABCKASEFI repository and install ABCKASEFI from the video add-ons.
4. Open the add-on settings and enter the catalog address and the API token.

### Install from a file source

The whole site is a plain list of links, so Kodi can use it as a file source. In Kodi open Settings, File manager, Add source, and enter the address <https://mirecekd.github.io/plugin.video.abckasefi/>. Then open Add-ons, Install from zip file, choose this source, open `repository.abckasefi` and select `repository.abckasefi.zip`. After that, continue with steps 3 and 4 above.

## Settings

| Setting | What it does |
| --- | --- |
| Catalog address | Address of the abckasefi-catalog service, `http://` or `https://`. |
| API token | Token required by the catalog. It is hidden while typing. |
| Items per page | Titles loaded on one page of a list: 20 to 200 in steps of 10, default 100. |
| Title language | Czech, Slovak or English titles and descriptions. Default Czech. |
| Set up from a phone (QR code) | Shows a QR code for filling in the settings in a phone browser. |
| Test connection | Checks the catalog with the current address and token. |

## Phone setup with a QR code

Typing a long address and token with a TV remote is tedious. Choose "Set up from a phone (QR code)" in the settings. Kodi shows a QR code and starts a small web server on the local network for at most ten minutes. Scan the code with a phone on the same network, fill in the form and press Save. The server accepts one submission and then stops. The form never shows the stored token; leave the token field empty to keep the current one.

The setup page is served over plain HTTP on your local network and is protected by a one-time secret in the address. Use it only on a network you trust.

## Privacy

The API token and the catalog address are stored in plain text in the add-on's `addon_data` folder of your Kodi profile, as Kodi does for all add-on settings. Poster URLs carry the token as well (image requests cannot send headers), so they also appear in Kodi's texture database (`Textures13.db`) on the same device. The add-on never writes the token to the Kodi log. Over plain `http://` the token travels unencrypted on your network; for anything beyond a trusted home network put the catalog behind HTTPS. A redirect from `https://` to `http://` is refused so the token is never sent in clear because of it.

## Watched series

A series folder is marked watched in a list once Kodi's database says every episode was played. The add-on learns how many episodes a series has when you open it, so the mark appears for series you have opened at least once.

## HTTPS certificates

HTTPS certificates are always verified. There is no option to turn the verification off, and no fallback that skips it. If the certificate cannot be verified (for example, because the device clock is wrong), the add-on shows an error and makes no connection. You can then check the date and time, update `script.module.certifi`, or use a different catalog address.

## Pagination

Letter and list screens are loaded page by page. The number of titles on a page is set by Items per page; a "Next page" entry at the end of a list loads the following page.

## Watched marks

Watched marks and resume points are Kodi's own. The add-on does not keep a separate watched database. Movies and episodes use the state that Kodi stores for the playback address, and seasons and series show how many episodes are watched based on the same data.

## Legal

This add-on hosts nothing, indexes nothing and distributes no content. It is a browser for a catalog service that you operate, and it passes playback to another add-on. What you play is your own responsibility.

## Support

If you find the add-on useful, you can support its development:

<div align="center">

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekd) [!["PayPal.me"](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?business=LJ5ZF7Q9KMTRW&no_recurring=0&currency_code=USD)

</div>

## License

MIT, see [LICENSE](LICENSE).
