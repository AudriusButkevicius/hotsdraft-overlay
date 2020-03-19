# hotsdraft-overlay
A small application that does computer vision based draft detection, queries [hotsdraft.com](http://hotsdraft.com) for best picks/bans, and
draws overlay with results.

![Example](./example.png)

This works purely based on screenshots and does not read or modify the games memory, therefore in my belief, is a perfectly legal application in terms of Blizzard T&C.

Sadly this has only been tested on 4k resolution, but in theory should work on a smaller resolution as well. Font sizes might need adjusting.

## Pre-requisites

* Python 3+
* Tesseract

## How to run this

You can download a packaged binary available in the [releases page](https://github.com/AudriusButkevicius/hotsdraft-overlay/releases)
This ships all required libraries other than Tessaract, which you still need to install externally and make sure it's at the right path.

If you don't trust the binary, you can always run it yourself:

1. Install Python 3+
2. Install Tesseract. Tesseract application should be at "C:\Program Files\Tesseract-OCR\tesseract.exe" or the path in `detection.py` should be modified. 
3. Clone the repo
4. Run `pip install -r requirements.txt` to install required libraries
5. Run `python hotsdraft_overlay/runner.py`
6. Once in draft, use `F8` to toggle visibility of the overlay. Use `F7` to refresh the suggestions.

## How to develop

I suggest using PyCharms IDE which seems to have sensible type completion for Python 3.

If you want to work on features that work on image processing, you can swap WindowCanvas for ScreenshotCanvas which works
off screenshots being fed from a directory. There are a few debug flags left in detection code to display subrectangles produced screenshot slicing code.

If you are working on developing a new layout, I suggest you switch to a ScreenshotCanvas, uncomment the line in `runner.py` redirecting application flow into `run_in_layout_build_mode`. Pressing `F8` in that mode reloads the file with the layout code and re-renders it.

## Known issues

1. Heroes with portraits with little features (lookin at you Malthael) sometimes fail to be detected
2. As of 2020-03-19, [hotsdraft.com](http://hotsdraft.com) does not include Deathwing
3. False-positive detections which should be addressed by item 6 in "Things that I think are worth working on"

## Things that I think are worth working on

1. Break the DraftSuggestionLayout into multiple smaller layouts to be composable:
    * Layout for pick suggestion names only
    * Layout for ban suggestion names only
    * Layout for trait display for picks
    * Layout for trait display for bans
2. Implement Qt based a tray icon, which would allow you to configure the application.
3. Add support for preferred role selection when submitting requests to [hotsdraft.com](http://hotsdraft.com).
4. Add support for including pre-picks as ally picked heroes when checking suggestions.
5. Move map detection to use SIFT oppose to Tessaract to speed up lookup/accuracy and remove a binary dependency.
6. Slice up hero selection image into 5 rectangles instead of one large image with 5 portraits. Each rectangle would represent one portrait and 
   the detection logic could be improved to permit only a single match with the highest number of matched features.
7. Add support for auto-detection/auto-display when in draft. This should be done after 5 is done, effectively only in draft when
   found a valid map. This would also enable auto-hide when draft finishes. Enables auto-refreshing.
8. Package the application with py2exe for novice users to download, use Github CI to produce that.
