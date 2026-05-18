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

## Implementation Notes

- Before adding UI, search for a nearby component that already solves the interaction.
- New shared UI should live with the existing UI/component structure and expose a small, predictable API.
- Prefer theme variables over hard-coded colors. Add a new variable only when the color represents a reusable semantic role.
- Use icons and microcopy to make actions discoverable, then rely on `Tooltip` for compact secondary context.
- Keep modal, panel, and toolbar interactions consistent with existing disclosure patterns.
