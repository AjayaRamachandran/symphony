# State Loading Rules

- Last Updated for Symphony v1.1, Feb 2026

### Old storage methods
Prior to Symphony v1.1, the program state was stored in the following format:

```
{
    (key, time, color) : Note(key, time, color, lead...)
    ... and so on
}
```

While this was efficient for location-based lookup times (one use case), its pitfall is that the structure bears no reference to color channels (used for playback and rendering). As such, the notes that needed to be rendered on a frame-by-frame basis were calculated from this hashmap containing all the notes.

To make this more computationally efficient, in Symphony v1.1 we change the structure of notes:

```
{
    "colorName" : [
        Note(pitch, time, duration),
        ... and so on
    ]
}
```

and when saving, we simplify even further:

```
{
    "colorName" : [
        {
            "pitch" : pitch
            "time" : time
            "duration" : duration
        },
        ... and so on
    ]
}
```

> (!) Initially we experimented with a dynamic channel storage. This means the notemap doesn't even store the color channels that are empty -- however, this caused a lot of headaches and had virtually no benefits (at least for now), so as of 2/4/26, the noteMap is initialized with all 6 color channels as empty lists.

### Conversion process
When loading old symphony files we do the following:

- Check what version the Symphony file is from (1.0 and earlier store the ProgramState as an object, 1.1 and newer store it as a dict, and also save their numbered version in that dict)
- If old, extract usable fields and set new defaults. In this process we also convert the old NoteMap to the new NoteMap:
    - This involves iterating through color by color, and for each color we loop through the full old noteMap and add any notes of that color to that list. There's a more computationally efficient way to do this, but it happens once at load time and already only takes < 1ms so I'm not going to try to make it any faster.
- If new, the noteMap is probably in savable format (no Objects) -- if so, convert into usable format (Note() objects) so we can use OOP render methods.

- File loaded. Return back to main.