<p align="center">
  <img src="https://www.dropbox.com/scl/fi/l0q1c2el848gt3wqeyvc2/SymphonyLogo.png?rlkey=rs2kxjanpmnpw3fywwqj3vj80&st=0ba0ujkq&raw=1" width="198" height="208">
  <h1 align='center'><b>Symphony</b></h1>
  <p style="font-size: 16px;" align='center'>Create something amazing.</p>
</p>


<p align="center">
<img src="https://img.shields.io/badge/React-blue?logo=React">
<img src="https://img.shields.io/badge/Node-darkgreen?logo=Node.js">
<img src="https://img.shields.io/badge/Python-navy?logo=Python">
<img src="https://img.shields.io/badge/Electron-gray?logo=Electron">  ˙ ˙ ˙  
<img src="https://img.shields.io/badge/Render-black?logo=Render">
<img src="https://img.shields.io/badge/Lucide-darkred?logo=Lucide">
</p>

<img src="https://www.dropbox.com/scl/fi/1cs50fias0t2lpy6cfnjw/READMEPIC1.png?rlkey=efavhqi1zc8oiclzh0mwjanyr&st=gaf7ggos&raw=1" style="border-radius: 5px;">

## Overview

**[Symphony](https://powerscore.vercel.app/)** is a music creation software for people of all skill levels. With a strong focus on **intuitive design**, Symphony takes away the usual learning curve that makes many creatives shy away from conventional tools. For drawing up a simple musical idea, conventional DAWs are *far too complex*, requiring lengthy project setups, and catering to high-power users, which can clutter the interface for simple experimentative sessions. *Symphony* aims to provide that space where users can **jump right in and start drafting**, keep the user experience simple yet powerful.

When you're ready to move to the more technical phase, *Symphony* gives you some power features like **stacking multiple sounds** or **playing with wave types**, but importantly, the app lets you ***export your projects*** into a myriad of standard music file types, ensuring you can continue your creative flow without restarting.

## Codebase Information

*Symphony* is made with what I'm calling the **RENSP** stack <small><small>*(I don't think that'll catch on)*</small></small>. It consists of <u>**R**</u>eact, <u>**E**</u>lectron, <u>**N**</u>ode, <u>**S**</u>DL2, and <u>**P**</u>ygame.Mixer; A slightly unconventional stack, but it's tailor-fit at each step of the column to ensure maximum efficiency and minimal boilerplate.

<img src='https://www.dropbox.com/scl/fi/m7vp194gkiovxp7oydcbk/StackBreakdown.jpg?rlkey=628b5o9vmvycfaugiqdxvmaa9&st=95zmxofb&raw=1' style='border-radius:5px;'>

- **React on the Front-End:** Symphony uses a conventional React component structure for handling all the frontend logic of the Project Manager. We build with **Vite** for rapid hot-swapping, which accelerated dev time.

- **Electron as the RT Environment:** Simple, and avoids the complexities of config needed for "faster" frameworks. Fast debugging with the native browser DevTools window were really useful for fast testing.

- **Node for the Backend:** This is really as a sub-layer of Electron, which interfaces with Node's IPC renderer to handle file management and state logic of the Project Manager.

- **SDL2 for the Editor Interface:** This is done via Python's Pygame library, and allows us to essentially take advantage of precise, pixel-level rendering of complex elements beyond the capabilites of traditional DOM-style renders, and since we're doing it all inside of the Python main process we can handle all system functionality *under the same hood as the frontend* without needing compartmentalization *hell* with endpoints and external calls. This did mean we spent a good while reconstructing basic UI functionality from scratch, like scrolling, selecting, dragging, etc, but the end result is total program control, which is worth it when designing a tightly integrated editor and playback system.

- **Pygame.Mixer for Audio:** Another just... obvious option. We initially experimented with the Simpleaudio library when starting out, but found that switching to Pygame.Mixer was a small migration effort that completely eliminated what used to sub-minute crashes from segmentation faults in the Simpleaudio library. Mixer also runs significantly faster, reducing playback latency.

## Design Language

Symphony has a clean, consistent UI design language we're calling Slate. It features, a dark, yet contrast-rich look with plenty of design flair, while adhering to strict principles of design.
### Typeface Choice

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/yknqytf9lqdtr0olzhvsq/Font-Choice.jpg?rlkey=1ab5jugpax1nke7ro6ng4mrgs&st=yv2yi9vz&raw=1' width='70%'>
</p>

There are **two** major fonts used across Symphony: *Instrument Sans*, and *Inter*.

- ***Instrument Sans*** is recognizable by its slightly wide stance, smaller natural kerning, and low x-height. This makes it great for big titles, where legibility is not an issue. It also has a touch of character, with features like the tilted terminals visible in letters like the lowercase 't', without being too bold or divisive.

- ***Inter*** is characterized by its simplicity, sacrificing uniqueness for legibility. It's designed to be readable at even tiny sizes, with its very high x-height and consistent minimum internal spacing to avoid clashing. As both the project manager and editor feature text at small sizes throughout, Inter was a clear choice.

### Button Design
Across the system, we have buttons that accomplish different tasks, from small, single-step actions that are stateless, to heavier tasks that advance UX flow in some way, all the way up to huge actions that move the program to a completely different state. To communicate each of these three abilities, we have a design language built into the buttons.

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/ea1aptg9w9rw3bj1yk8qs/Button-Design.jpg?rlkey=oii350uwr275ausjorw1g3dml&st=6teh57aa&raw=1' width='100%'>
</p>

- **Standard Buttons** can be seen in the toolbar or in left and right panels. They are often stateless (but not always), and don't command user attention, as if all such buttons were bold, they would be fighting for attention.
- **Heavy Buttons** can be seen in modals, often reading "Next" or "Done" or "Delete". These perform big actions, including closing the modal itself, and need to distinguish themselves from the rest of the options on the modal.
- **Call-to-Action** is used in the "Open in Editor" button. This is a special button as it launches a whole separate window, and represents the program state changing. This button style is used incredibly sparingly (so far, only once) as it is very commanding of attention.

### Optical Sizing
A common example used to explain optical sizing is the [circles and squares example.](https://bjango.com/articles/opticaladjustments/) In *Symphony* (and many other softwares) a more common optical sizing is seen: large and small text. A common misconception is that all left or right-justified text should align to the same pixel -- however, this will lead to the smallest text feeling pushed further to the edge than the larger text, since more of its details are optically closer to the edge. We must shift smaller text away from the edge to keep them feeling optically aligned.

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/4c6ilgee4j6ma57kponbc/Optical-Spacing.jpg?rlkey=0j8wzvw9xi1o7vxm0939laugp&st=d2h90bjj&raw=1' width='90%'>
</p>

As you can see in the above example, the red line is several pixels to the right of the blue line, however the text is **optically aligned;** without the lines pointing it out, the text actually appears more natural than if they were pixel-aligned. Additionally, the image shows the effect of optical kerning as well -- the percentage of letter widths that should be proportional to the empty space increases as the text gets smaller. This keeps text feeling breathable at all sizes. In *Symphony*, this can be seen in the small letterforms in the toolbar, where wide kerning allows the text to remain readable even at < 9px.

### Directing Attention
Symphony has many *modals*. These are floating widgets that display task-sensitive information, and require the user's immediate attention. To direct the user's attention to the content of the modals, in a manner that does not clutter their view, we employ a subtle blur to everything else.
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/iqx5688ge67nk7rtcjosl/Directing-Attention.jpg?rlkey=tk445ffzs6fm18znvr2yab1n8&st=1ftomejv&raw=1' width='70%'>
</p>

### Other Design Choices: Bold Size Effects, Intuitiveness
A little known fact: Bold text optically looks *smaller* than thin text. The reasons for this phenomenon are not well-stated anywhere, but the primary reason is that your eyes see the size of text generally as the distance between the midpoints of parallel lines, which, when the text gets bolder without getting taller, actually *decreases*. In some modals, where simply bolding the text would make it appear slightly smaller, throwing off the visual hierarchy, we increase the size by around 1px to compensate. This effect is *incredibly subtle*, but is more noticeable when it's *not* used.
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/yef3ytl1u5malkg98e7o7/Boldness-on-Sizing.jpg?rlkey=57c3l260eaa5wbe20kmsiydev&st=p44tungh&raw=1' width='65%'>
</p>
On top of our extensive button design considerations, we also need to meld practicality with design aesthetics. While text is great at describing the purpose of a button, practically, it is impossible to give text to every button on the screen. In areas like the toolbar, we use icons instead. Here, we are trading initial affordance with better space usage. But to keep users from having to guess what buttons do, we employ hover tooltips on all icon-only buttons, and for any text fields where internal text is truncated for space. This ensures that all navigational information is accessible, even if not visible at once. <br><br/>
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/3a7qy0d5lhugk1kkeyujq/Intuitiveness.jpg?rlkey=4gwbovn39g86qcdbk2b2oy3fw&st=zp5tqk9h&raw=1' width='55%'>
</p>



## *Footnote:* Technical Challenges & Future Considerations

*Symphony* is still under active development, but we can already identify some pain points in development and crutches that might hinder its widespread adoption, but these are things that we want to see crop up as they pan out, because, to be honest, I really don't know how big each one is until it's in the hands of testers. (I'm subtly urging you to download this and test it yourself \*wink wink\*)

- **Growing codebase:** Codebase management as a solo developer is definitely a major challenge. Pieces interact with each other across the entire platform, components calling other components from wildly different places -- I do believe that with this project, it was almost a must to keep my components and styles organized. Thus, the repo, while large, is well-fragmented into digestible pieces.

- **Monofile editor:** Initially a method to keep function call order consistent (and Z-layering easy) and essentially create a easy-to-access single file to handle the editor processes, has now become an absolutely gigantic "monofile" editor that is over 1,400 lines of code long. Making changes in this file is cumbersome, as it often involves injecting new code at precarious locations in the file. If I had the time, I would completely refactor the inner editor to adopt a similar component structure as the project manager, if not for the visuals then at least breaking up various tasks of the Editor into multiple files to avoid this "hunting".

- **Performance Limits:** While not imminent, the Editor, which runs on a realtime loop rather than an Event-based DOM, can put strain on lower-end PCs, when in fullscreen, when the app is pushing a lot of pixels manually. This is in part due to Python being a slower language but also a lack of optimization in the rendering process -- we have optimized a lot **WHAT** we are rendering (screenspace culling, hashmapping, object-oriented buttons) but not **HOW** we are rendering it (example: pausing screen updates when blurred focus, event-based UI updates, etc.).