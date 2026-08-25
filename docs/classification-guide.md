# Classification guide

## Principles

Each record has one `primary_category` for predictable browsing and one
`scope_status`. Categories describe the project's main subject. Scope describes
its distance from the index's centre. Neither field expresses quality, maturity,
popularity, or endorsement.

Use the most specific category that describes the repository's principal
contribution. When several categories apply, choose the one a new reader would
most reasonably use to look for the project. GitHub topics remain independent
discovery terms and do not override human classification.

## Boundary guidance

- Use **musical instrument acoustics** for projects studying how instruments
  generate, radiate, or transmit sound.
- Use **physical and computational acoustics** for general numerical solvers,
  wave models, and simulation methods not centred on instruments or rooms.
- Use **room and virtual acoustics** for room simulation, impulse responses,
  reverberation, and virtual acoustic environments.
- Use **spatial audio and auralization** when rendering, binaural/ambisonic
  representation, source localization, or perceptual spatial reproduction is central.
- Use **virtual instruments and synthesis** for playable synthesis systems,
  synthesis engines, sound generators, and instrument emulations.
- Use **instrument recognition and datasets** for instrument-centred corpora,
  recognition, transcription, alignment, or learned models.
- Use **instrument design and hardware** for construction, electronics,
  controllers, augmented instruments, and fabrication.
- Use **organology and instrument knowledge** for taxonomies, ontologies,
  museum/collection data, and structured instrument knowledge.
- Use **meta resources** only when the repository's main contribution is a
  curated index or guide rather than the underlying software or data.

The normative identifiers, bilingual labels, definitions, and scope notes are in
`data/vocabularies/categories.json`.

## Changing a classification

A change should include a short rationale. Category changes are curator-reviewed
data changes and must never be made automatically from keywords or repository
topics.
