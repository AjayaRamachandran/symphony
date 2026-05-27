# Agent Guidance

This project has a restrained, intentional UI language. When making changes, preserve the existing design system before inventing new patterns.

## Design Principles

- Use Inter as the base UI font. Use Instrument Sans for display moments such as headings, panels, modal titles, and other high-emphasis labels.
- Prefer progressive disclosure. Show the core action first, then reveal secondary information through panels, menus, modals, details states, or tooltips when the user asks for more.
- Reuse existing UX components whenever possible. If the same interaction is likely to appear again, create a reusable component instead of a one-off implementation.
- Keep colors in the theme. Use the CSS variables defined in `src/universal-styling/index.css` for surfaces, text, primary actions, secondary accents, status colors, and neutrals.
- Avoid rampant gradients, decorative glow, and novelty visual effects unless they already exist in the surrounding UI and serve a clear purpose.
- Avoid anti-patterns like ping circles, noisy loading flourishes, or other obviously vibe-coded embellishments. Motion should clarify state, not decorate it.
- For consumer-facing launch, loading, onboarding, and empty states, avoid implementation language like shell, backend, handoff, Tauri, pywebview, process, or launcher. Describe only the product-facing state the user cares about.
- Splash and loading screens should feel like branded surfaces, not UI nested inside extra boxes, unless the surrounding product surface already establishes that card pattern.
- Use the custom `Tooltip` component from `src/ui/Tooltip.jsx` for affordance, shortcuts, and compact explanation. Do not build ad hoc tooltip behavior.
- Keep interface density calm and legible. Favor subtle borders, theme-aware contrast, and existing spacing rhythms over heavy decoration.
- Match the surrounding component style before adding a new convention. Local consistency beats abstract preference.
- For piano-roll and note-grid surfaces, reserve the darkest background values for negative space such as gaps between cells. Do not brighten the note cells to create this contrast; preserve intentional cell shading and change the surrounding/gap surface instead.
- Keep editor measurement chrome neutral. Measure tickers, rulers, zoom controls, scrollbars, and debug readouts should not use primary/brand color unless they represent an actual selected or active musical state.
- Pitch labels should read like labels, not debug badges: use normal spacing, moderate weight, left alignment in the pitch rail, and existing musical glyph assets such as the flat icon instead of text approximations like `b`.

## Implementation Notes

- Before adding UI, search for a nearby component that already solves the interaction.
- New shared UI should live with the existing UI/component structure and expose a small, predictable API.
- Prefer theme variables over hard-coded colors. Add a new variable only when the color represents a reusable semantic role.
- Use icons and microcopy to make actions discoverable, then rely on `Tooltip` for compact secondary context.
- Keep modal, panel, and toolbar interactions consistent with existing disclosure patterns.
- Prefer camelCase for new Python names and avoid `_private_by_convention` naming unless an external framework requires a specific method name.

**Do not run build scripts automatically.** If building or rebuilding is required, explicitly instruct the user to run the relevant build commands, as these scripts can be time-consuming.

**Do not run the dev build automatically either, unless specifically checking log outputs.** This is because this is a blocking, persistent behavior that the user would rather do. If the message is simply "test this out to see if it's better after changes", then there's no need for the agent to run the dev build. Instruct the user to do so instead. 