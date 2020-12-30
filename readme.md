# pierogis-bot

A bot that cooks pierogis.

A `pierogi` is just a stupid name for an image and to `cook` is just a stupid name for image processing.

This code acts on behalf of [@pierogis_chef](https://twitter.com/pierogis_chef). 
[@pierogis_bot](https://twitter.com/pierogis_bot) is used for testing.

Making an order involves tagging @pierogis_chef while referencing an image (or set of images) that you would like in your meal.

Referencing means
- tweeting with media
- replying to a tweet with media 
- quote tweeting a tweet with media 
- replying to a tweet with media with a quoted tweet with media

This will trigger the chef to cook and serve your order in reply.

The chef will also (soon) serve private tables if you send a dm with a picture.

##recipes

There are à la carte recipes that you can use in the text of a tweet to specify your order.
By default (if there is no text in the tweet), your order will be "chef's choice".

Multiple recipes can be processed in order when separated by semicolons. Options can also be included with the recipe.

###sort
```
@pierogis_chef sort -l 80 -u 180 -t 0
```
The `sort` recipe creates boundaries at certain pixels and sorts contiguous pixels within these bounded groups across the height or width of the pierogi based on intensity.

Put another way, boundary pixels stay in place while the group of pixels spanning the sort direction until the next boundary pixel are sorted by intensity.

####options
Bounding pixels are those with intensities outside of the lower (`-l`) and upper (`-u`) thresholds.
You can specify what direction to sort in with the turns (`-t`) option.

- Intensity is the average of the rgb values of a pixel.
- The rgb values of a white pixel are (255, 255, 255) and (0, 0, 0) for black pixels.
- Setting `-l 80` and `-u 180` means that pixels that have an average rgb less than 80 or higher than 180 will set the boundaries for groups of pixels to sort.
- The default sorting direction is low -> high intensity, bottom -> top
- Setting `-t 1` means the sort direction will make one clockwise 90 degree turn from the default (low -> high intensity, left -> right)

This is based on [Kim Asendorf's algorithm](https://github.com/kimasendorf/ASDFPixelSort) and the [pixelsort](https://github.com/satyarth/pixelsort) package

###quantize
NOT IMPLEMENTED YET
```
@pierogis_chef quantize -k
```
The `quantize` recipe creates a color palette from the pierogi and sets each pixel to the nearest color in the palette.

####options
Use `-k` to specify the number of colors to include in the palette

###multiple recipes

Separate recipes with `;`

```
@pierogis_chef sort; quantize -k
```
This will first sort the pixels with default settings, then quantize the output of that to a color palette.