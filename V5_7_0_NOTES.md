# VastuAI Platform v5.7.0

## Mobile Responsive UI

This release prepares the existing VastuAI Streamlit product for Android/mobile browser testing while preserving the v5.6.1 business logic.

### Mobile behaviour
- Streamlit sidebar now uses automatic responsive state instead of being forced open.
- Multi-column layouts stack into a single vertical flow below 768 px.
- Property cards, metrics, forms and action areas become full-width on phones.
- Buttons and form submit controls are touch-friendly and full-width.
- Tabs scroll horizontally on narrow screens instead of compressing labels.
- Dataframes remain readable through horizontal scrolling.
- Images and charts are constrained to the device viewport.
- Mobile typography and spacing are slightly tightened without changing the desktop design system.
- Inputs use mobile-safe font sizing to avoid unwanted browser zoom.

### Scope
No scoring, LangGraph, numerology, Vastu, Builder analysis, database, buyer workspace, reports or AI Consultant logic was changed.

### Next
After Android-browser validation, the same responsive build can be deployed behind HTTPS and wrapped as the VastuAI Mobile Beta/PWA.
