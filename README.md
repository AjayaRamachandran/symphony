<p align="center">
  <img src="./src/assets/icon-dark-512.png" width="128" height="128">
  <h1 align='center'><b>Symphony</b></h1>
  <p style="font-size: 16px;" align='center'>Let's create something amazing.</p>
</p>

<p align="center">
<img src="https://img.shields.io/badge/React-blue?logo=React">
<img src="https://img.shields.io/badge/Node-darkgreen?logo=Node.js">
<img src="https://img.shields.io/badge/Python-navy?logo=Python">
<img src="https://img.shields.io/badge/Electron-gray?logo=Electron">  ˙ ˙ ˙  
<img src="https://img.shields.io/badge/Vercel-black?logo=Vercel">
<img src="https://img.shields.io/badge/Lucide-darkred?logo=Lucide">
</p>

<img src="https://www.dropbox.com/scl/fi/sj3qb5zu4x82k8s6785rn/Symphony-SS.png?rlkey=lxpta4hjcdhybl4400nrql20o&st=wpe8nxt3&raw=1" style="border-radius: 5px;">

## Overview: *Monorepo*

**[Symphony](https://powerscore.vercel.app/)** is a music creation software for people of all skill levels. With a strong focus on **intuitive design**, Symphony takes away the usual learning curve that makes many creatives shy away from conventional tools. For drawing up a simple musical idea, conventional DAWs are *far too complex*, requiring lengthy project setups, and catering to high-power users, which can clutter the interface for simple experimentative sessions. *Symphony* aims to provide that space where users can **jump right in and start drafting**, keeping the user experience simple yet powerful.

When you're ready to move on to the more technical phase, *Symphony* gives you power features like **stacking multiple sounds** or **setting up simple instruments** to export into audio formats (.mp3, .flac, .wav), but also lets you ***export your projects*** into a myriad of standard music file types (.midi, .musicxml), ensuring you can continue your creative flow without restarting.

## Codebase Information

*Symphony* is made with what I'm calling the **RENSP** stack <small><small>*(I don't think that'll catch on)*</small></small>. It consists of <u>**R**</u>eact, <u>**E**</u>lectron, <u>**N**</u>ode, <u>**S**</u>DL2, and <u>**P**</u>ygame.Mixer; An unconventional stack, but it's tailor-fit at each step of the column to ensure maximum efficiency and minimal boilerplate.

<img src='https://www.dropbox.com/scl/fi/m7vp194gkiovxp7oydcbk/StackBreakdown.jpg?rlkey=628b5o9vmvycfaugiqdxvmaa9&st=95zmxofb&raw=1' style='border-radius:5px;'>

- **React on the Front-End:** Symphony uses a conventional React component structure for handling all the frontend logic of the Project Manager. We build with **Vite** for rapid hot-swapping, which accelerated dev time.

- **Electron as the RT Environment:** Simple, and avoids the complexities of config needed for "faster" frameworks. Fast debugging with the native browser DevTools window were really useful for quick testing.

- **Node for the Backend:** This is really as a sub-layer of Electron, which interfaces with Node's IPC renderer to handle file management and state logic of the Project Manager.

- **SDL2 for the Editor Interface:** This is done via Python's Pygame library, and allows us to essentially take advantage of precise, pixel-level rendering of complex elements beyond the capabilites of traditional DOM-style renders, and since we're doing it all inside of the Python main process we can handle system functionality like sound generation and playback *under the same hood* as the frontend logic. This did mean I spent a good while reconstructing basic UI functionality from scratch, like scrolling, selecting, dragging, etc, but the end result is total program control, which is worth it when designing a tightly integrated editor and playback system.

- **Pygame.Mixer for Audio:** Another just... obvious option. I initially experimented with the Simpleaudio library when starting out, but found that switching to Pygame.Mixer was a small migration effort that completely eliminated what used to be frequent, inexplicable crashes from segmentation faults in the Simpleaudio library. Mixer also runs significantly faster, reducing playback latency.

## Design

Symphony has a clean, consistent UI design language we're calling Slate. It features a dark, yet contrast-rich look with plenty of design flair, while adhering to strict principles of design.
### Typeface Choice

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/yknqytf9lqdtr0olzhvsq/Font-Choice.jpg?rlkey=1ab5jugpax1nke7ro6ng4mrgs&st=yv2yi9vz&raw=1' width='70%'>
</p>

There are **two** major fonts used across Symphony: *Instrument Sans*, and *Inter*.

- ***Instrument Sans*** is recognizable by its slightly wide stance, smaller natural kerning, and low x-height. This makes it great for big titles, where legibility is not an issue. It also has a touch of character, with features like the tilted terminals visible in letters like the lowercase 't', without being too bold or hard to read.

- ***Inter*** is characterized by its simplicity, sacrificing uniqueness for legibility. It's designed to be readable at even tiny sizes, with very high x-height and consistent minimum internal spacing to avoid clashing. As both the project manager and editor feature text at small sizes throughout, Inter was a clear choice.

### Button Design
Across the system, we have buttons that accomplish different tasks, from small, single-step actions that are stateless, to heavier tasks that advance UX flow in some way, all the way up to huge actions that move the program to a completely different state. To communicate each of these three abilities, we have a design language built into the buttons.

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/ea1aptg9w9rw3bj1yk8qs/Button-Design.jpg?rlkey=oii350uwr275ausjorw1g3dml&st=6teh57aa&raw=1' width='100%'>
</p>

- **Standard Buttons** can be seen in the toolbar or in left and right panels. They are often stateless (but not always), and don't command user attention, since if all such buttons were bold, they would be fighting for attention.
- **Heavy Buttons** can be seen in modals, often reading "Next" or "Done" or "Delete". These perform big actions, including closing the modal itself, and need to distinguish themselves from the rest of the options on the modal.
- **Call-to-Action** is used in the "Open in Editor" button. This is a special button as it launches a whole separate window, and represents the program state changing. This button style is used incredibly sparingly (so far, only once) as it is very commanding of attention.

### Optical Spacing
A common example used to explain optical sizing is the [circles and squares example.](https://bjango.com/articles/opticaladjustments/) In *Symphony* (and many other softwares) a more common optical sizing problem is seen: large and small text. A common misconception is that all left or right-justified text should align to the same pixel -- however, this will lead to the smallest text feeling pushed further to the edge than the larger text, since more of its details are optically closer to the edge. We must shift smaller text away from the edge to keep them feeling optically aligned.

<p align='center'>
<img src='https://www.dropbox.com/scl/fi/4c6ilgee4j6ma57kponbc/Optical-Spacing.jpg?rlkey=0j8wzvw9xi1o7vxm0939laugp&st=d2h90bjj&raw=1' width='90%'>
</p>

As you can see in the above example, the red line is several pixels to the right of the blue line, however the text is **optically aligned;** without the lines pointing it out, the text actually appears more natural than if they were pixel-aligned. Additionally, the image shows the effect of optical kerning as well -- the percentage of letter widths that is proportional to the empty space *increases* as the text gets smaller. This keeps text feeling breathable at all sizes. In *Symphony*, this can be seen in the small letterforms in the toolbar, where wide kerning allows the text to remain readable even at < 9px.

### Directing Attention
Symphony has many *modals*. These are floating widgets that display task-sensitive information, and require the user's immediate attention. To direct the user's attention to the content of the modals, in a manner that does not clutter their view, we employ a subtle blur to everything else.
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/iqx5688ge67nk7rtcjosl/Directing-Attention.jpg?rlkey=tk445ffzs6fm18znvr2yab1n8&st=1ftomejv&raw=1' width='70%'>
</p>

### Other Design Choices: Bold Size Effects, Intuitiveness
**Little known fact:** Bold text optically looks *smaller* than thin text. The reasons for this phenomenon are multilayered, but the primary reason is that your eyes see the size of text as the distance between the **centers** of parallel curves in the letterform, which, if the text gets bolder without getting taller, actually *decreases* in length. In some modals in *Symphony*, where simply bolding the text could make it appear slightly smaller and throwing off the visual hierarchy, we increased the size by around 1px to compensate. This effect is *incredibly subtle*, but it's more noticeable when it's *not* used.
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/yef3ytl1u5malkg98e7o7/Boldness-on-Sizing.jpg?rlkey=57c3l260eaa5wbe20kmsiydev&st=p44tungh&raw=1' width='65%'>
</p>
On top of our extensive button design considerations, we also need to work practicality into design aesthetics. While plain text is great at describing the purpose of a button, practically it is impossible to give text to every button on the screen. In areas like the toolbar, we use icons instead. Here, we are trading initial affordance with better space usage. But to keep users from having to guess what buttons do, we employ hover tooltips on all icon-only buttons, and for any text fields where internal text is truncated for space. This ensures that all navigational information is accessible, even if not visible at once.

> This is also closely aligned with a different design ideology we follow in Symphony, **continued intent**. This is the idea that an action should suggest the actions that follow it, like creating a symphony -> opening created symphony or exporting -> highlighting exported file. Tooltips, which came before continued intent was formalized, is now a subset of the larger design framework.

<br><br/>
<p align='center'>
<img src='https://www.dropbox.com/scl/fi/3a7qy0d5lhugk1kkeyujq/Intuitiveness.jpg?rlkey=4gwbovn39g86qcdbk2b2oy3fw&st=zp5tqk9h&raw=1' width='55%'>
</p>

## *Footnote:* Technical Challenges & Future Considerations

- **Growing codebase (monorepo architecture):** Codebase management as a solo developer is definitely a major challenge. Pieces interact with each other across the entire platform, components calling other components from wildly different places -- I do believe that with this project, it was almost a must to keep my components and styles organized. Thus, the repo, while large, is well-fragmented into digestible pieces. With v1.1, big changes here include splitting up the "monofile" editor program into a scoped, organized set of feature-oriented files that build into a single executable.

- **Performance:** The editor GUI, which is written in Python and uses a real-time game library for UI logic, was originally running on a game loop, which wasted a lot of compute, especially if the program was left idle. While this was okay for the limited capabilities of version 1.0, I knew that in order to add new GUI elements and app functionality, this framework was too fragile and slow. Thus, with v1.1, we have implemented deferred hierarchical rendering (a.k.a. lazy rendering), which essentially intelligently decides which UI elements and groups of elements actually need to update each frame, and to sit idle when the user is inactive (vastly reducing idle compute).

- **Load Times:** On some devices, load times were taking up to 90 seconds. This was simply unacceptable, and caused by the Python runtime needing to spin up from nothing every time the editor would need to be called upon. To combat this, v1.1 uses a daemon architecture that avoids spin up times by keeping the python program pre-loaded while the project manager is running, and simply calling upon it to open the GUI.

- **Inter-Process Communication:** We're using multiple languages and frameworks, and it was imperative that there was a clean mode of communication between programs to convey user settings, project configurations, and task calls. The result of ideating solutions to this problem was essentially a proper JSON-file-based API I'm calling the Process Command Architecture, which wraps writes and polls to a common json file into what is essentially API calls.