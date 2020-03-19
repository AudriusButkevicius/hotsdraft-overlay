# hotsdraft-overlay
A small application that does computer vision based draft detection, queries hotsdraft.com for best picks/bans, and
draws overlay with results.

![Example](./example.png)

Sadly this has only been tested on 4k resolution, but in theory should work on a smaller resolution as well.

#### Pre-requisites

* Python 3+
* Tesseract

#### How to run this

1. Install Python 3+
2. Install Tesseract. Tesseract application should be at "C:\Program Files\Tesseract-OCR\tesseract.exe" or the path in `detection.py` should be modified. 
3. Clone the repo
4. Run `pip install -r requirements.txt` to install required libraries
5. Run `python hotsdraft_overlay/runner.py`
6. Once in draft, use `F8` to toggle visibility of the overlay. Use `F7` to refresh the suggestions.

#### Things that I think are worth doing

1. Break the DraftSuggestionLayout into multiple smaller layouts to be composable:
    * Layout for pick suggestion names only
    * Layout for ban suggestion names only
    * Layout for trait display for picks
    * Layout for trait display for bans
2. Implement a tray icon, which would allow you to configure the application 
3. Add support for preferred role selection
4. Add support for including pre-picks as ally picked heroes (essentially just a new layout).
5. Move map detection to use SIFT oppose to Tessaract to speed up lookup/accuracy and remove a binary dependency.
6. Slice up draft image into 5 rectangles instead of one larger image. Each rectangle would represent one portrait and 
   the detection logic could be improved to permit only a single match with the highest number of matched features.
7. Add support for auto-detection/auto-display when in draft. This should be done after 5 is done, effectively only in draft when
   found a valid map. This would also enable auto-hide when draft finishes. Enables auto-refreshing.
