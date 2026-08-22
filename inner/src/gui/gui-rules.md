# GUI Rules
The `Frame` object, which holds elements within it, has accepted style rules that define how it renders, similar to css styling. Below is an enumeration of the accepted fields:
```python
"background"    : list[int, int, int, int]                          # default: gui.COLOR_TRANSPARENT
"border"        : int | list[int, int, int, int]                    # default: 0
"border-color"  : list[int, int, int, int]                          # default: gui.COLOR_BORDER
"rounding"      : "sm" | "lg" | int | list[int, int, int, int]      # default: 0 (rounding disabled if border is not int)

"display"       : "flex" | "absolute" | "fixed"                     # default: nest
"offset"        : list[int, int]                                    # default: [0, 0]
"orient"        : "row" | "col"                                     # default: row
"align"         : "center" | "top" | "bottom" | "spread"            # default: top
"justify"       : "center" | "left" | "right" | "spread"            # default: left
"sizing"        : list["fit" | "fill" | int, "fit" | "fill" | int]  # default: fit
"padding"       : int | list[int, int, int, int]                    # default: 0
"gap"           : int                                               # default: 0
```


## Implementation
We want resize calculations and general rerenders to be minimized; here is the logic to do so:

### Sizing
This is the most complex calculation in some cases. The way we must do these is that when a frame's size is recomputed, we look at any frames that are its children, and update their dimensions accordingly. This top-down action allows us to avoid polling.

Moving in one direction like this also means that we have a priority order for clashing sizing logic. placing a 'fit' element wrapping around a 'fill' element will prioritize the parent; meaning that the fill is treated like a fit. This order is, of course, arbitrary, but I have chosen it to be this way to prefer UIs that wrap content rather than fill the screen.


# Reuse bin
```python
        if isinstance[border, tuple]:
            borderT = border[0]
            borderR = border[1]
            borderB = border[2]
            borderL = border[3]
        else:
            borderT = border
            borderR = border
            borderB = border
            borderL = border

        if isinstance[rounding, tuple]:
            roundingT = rounding[0]
            roundingR = rounding[1]
            roundingB = rounding[2]
            roundingL = rounding[3]
        elif isinstance[rounding, str]:
            roundingT = LG_ROUND if rounding == "lg" else SM_ROUND
            roundingR = LG_ROUND if rounding == "lg" else SM_ROUND
            roundingB = LG_ROUND if rounding == "lg" else SM_ROUND
            roundingL = LG_ROUND if rounding == "lg" else SM_ROUND
        else:
            roundingT = rounding
            roundingR = rounding
            roundingB = rounding
            roundingL = rounding
```