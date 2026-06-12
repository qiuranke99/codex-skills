# 02_good_shotlist_examples.md

Knowledge file for `Storyboard Shot Planner`.

This file gives reusable examples of good shot-list logic and clean handoff specs for `Rough Storyboard Sketch Generator`.

The examples are original composites. They are not copied from films, ads, or web templates. Each example favors visible camera logic, sequence progression, scale/continuity, and storyboard readability over vague prompt language.

## Example 1: Four-Shot Surreal Street Sequence

Use case: a surreal city sequence similar to "a Japanese schoolgirl discovers she has become a giant in the street."

### 1. Input Brief

A teenage girl in a Japanese school uniform walks through a rainy Tokyo crossing after school. She suddenly realizes the city has shrunk around her, or she has grown into a giant. The sequence should feel surreal, not monstrous. It needs to be readable as rough storyboard panels.

### 2. Creative Constraints

- Keep her human, confused, and careful, not aggressive.
- Preserve rainy urban geography and left-to-right screen direction.
- Prove scale with taxis, pedestrians, crosswalk stripes, shop signs, and building windows.
- Avoid destruction fantasy unless explicitly requested.
- Sequence length: 4 shots.

### 3. Shot List Table

| Shot ID | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|
| SH_001 | Establish normal city baseline and character identity | Wide shot | Eye-level street corner | Natural 35mm street feel | Locked-off | Girl with navy uniform and red ribbon steps into rainy crossing among normal pedestrians | Girl on left third, umbrellas and taxis crossing frame | Normal scale baseline; red ribbon, black bob, wet loafers locked |
| SH_002 | Reveal first scale anomaly through POV-like discovery | Medium close-up | Slight high angle over her shoulder | Mild wide feel | Slow tilt down | She looks down; tiny taxis and umbrellas are now below her waistline | Her shoulder and hand frame top edge; tiny traffic below | Shoe longer than taxi; same uniform and rain |
| SH_003 | Prove giant scale through body action | Full wide shot | Low street-level angle looking up | Wide lens feel, vertical exaggeration | Static | She freezes mid-step, one foot hovering over taxis | Shoe dominates lower frame; buildings rise behind her; face small at top | Pedestrians thumb-sized near curb; shoe equals taxi length |
| SH_004 | Emotional payoff: careful giant in fragile city | Extreme wide shot | High rooftop angle | Compressed city-grid feel | Slow pullback | She crouches carefully between buildings, one hand braced on a roof | City blocks form grid; girl centered but curled inward | Knees higher than streetlights; no destroyed buildings; same left-to-right crossing direction |

### 4. Clean Handoff Specs

```yaml
SH_001
scene: rainy Tokyo crossing after school, normal-scale setup
shot_size: wide shot
camera_angle: eye-level from street corner
lens_feel: natural 35mm street feel, moderate depth
camera_movement: locked-off
main_subject: teenage girl in navy Japanese school uniform with red ribbon
main_action: she steps into the crosswalk with pedestrians and taxis around her
body_pose: walking left-to-right, shoulders slightly hunched under rain, school bag at right hip
composition: girl on left third; crosswalk diagonals lead toward traffic lights
foreground: blurred umbrella tops and wet curb edge
midground: girl, pedestrians, taxis at normal scale
background: shop signs, glass storefronts, rainy traffic signals
scale_reference: normal human height beside pedestrians and taxi roofline
continuity_lock: navy uniform, red ribbon, short black bob, wet loafers, rainy afternoon, left-to-right movement
must_preserve: normal scale baseline; wet reflections; no surreal scale yet
avoid: giant body, destroyed street, sunny weather, fantasy costume

SH_002
scene: same crossing, first surreal discovery
shot_size: medium close-up over shoulder
camera_angle: slight high angle looking down past her shoulder
lens_feel: mild wide feel, perspective makes street drop away
camera_movement: slow tilt down
main_subject: schoolgirl looking down at the suddenly tiny street
main_action: she lowers her gaze toward taxis and umbrellas below her
body_pose: shoulders tense, left hand hovering near chest, head tilted down
composition: her shoulder and hair frame upper left; tiny traffic fills lower right
foreground: edge of her red ribbon and damp hair strands
midground: her hand and torso
background: tiny taxis, umbrellas, crosswalk stripes far below
scale_reference: taxi roof is smaller than her loafer; umbrella dots below waist height
continuity_lock: same uniform and rainy crossing; left-to-right street geography
must_preserve: discovery through scale contrast, not horror
avoid: monster face, city destruction, extra giant characters

SH_003
scene: same crossing, scale proof
shot_size: full wide shot
camera_angle: low street-level angle looking up from near taxi bumper
lens_feel: wide lens feel with vertical exaggeration
camera_movement: static
main_subject: giant schoolgirl frozen mid-step
main_action: one foot hovers carefully above a row of stopped taxis
body_pose: knees bent, arms out for balance, eyes down, mouth slightly open
composition: shoe dominates lower foreground; body rises through center; buildings frame both sides
foreground: taxi hood and wet crosswalk stripe
midground: giant shoe, leg, stopped taxis, tiny pedestrians
background: vertical neon shop signs and high windows behind her shoulders
scale_reference: shoe length equals one taxi; pedestrians are thumb-sized near curb
continuity_lock: same red ribbon, navy uniform, wet black loafers, rainy afternoon
must_preserve: careful non-destructive posture; readable shoe-to-taxi scale
avoid: crushing cars, torn clothing, kaiju posture, chaotic explosions

SH_004
scene: rooftop view of same rainy district, emotional payoff
shot_size: extreme wide shot
camera_angle: high rooftop angle looking down into city grid
lens_feel: compressed urban-grid feel
camera_movement: slow pullback
main_subject: giant schoolgirl crouched between buildings
main_action: she braces one hand on a rooftop while trying not to touch traffic below
body_pose: crouched inward, elbows close, gaze down and worried
composition: city blocks form a grid; girl centered, curled into available space
foreground: rooftop railing and rain puddles
midground: girl's hand on roof, knees between streets
background: continuous blocks, tiny headlights, shop signs
scale_reference: her hand covers half a rooftop; knees rise above traffic lights
continuity_lock: same uniform, hair, ribbon, rainy district, no building damage
must_preserve: fragile-city feeling; human vulnerability; clear giant scale
avoid: triumphant superhero pose, collapsed buildings, random landmarks
```

### 5. Why This Shot List Works

- It starts with a normal scale baseline, then reveals the anomaly.
- Scale is shown through objects, not asserted with the word "giant."
- Shot sizes progress from wide baseline to subjective discovery to scale proof to payoff.
- The character remains emotionally legible and drawable.

### 6. Common Bad Version

```markdown
Make four cinematic shots of a giant Japanese schoolgirl in Tokyo. Show her walking in the city, then a dramatic close-up, then a wide action shot, then a beautiful final shot. Make it surreal and epic.
```

### 7. Why the Bad Version Fails

- No normal-scale baseline.
- No camera height, foreground/midground/background, or action.
- "Epic" pushes the generator toward destruction or hero fantasy.
- Scale is not tied to taxis, pedestrians, crosswalks, or buildings.

### 8. Readiness for Rough Storyboard Sketch Generator

Ready. Each shot has a dominant subject, camera relation, pose, depth layers, scale proof, and explicit avoid rules.

---

## Example 2: Six-Shot Product Commercial

Use case: product ad focused on product function, material, use action, and proof.

### 1. Input Brief

Create a six-shot commercial storyboard for a refillable water purifier bottle. The ad should show the problem, product reveal, use action, filter proof, portability, and final packshot. Product identity must stay consistent.

### 2. Creative Constraints

- Product: matte charcoal bottle, translucent vertical filter window, black cap, small blue status light.
- Keep label/window orientation consistent.
- Avoid exaggerated sci-fi effects; proof must be visually simple.
- Sequence length: 6 shots.

### 3. Shot List Table

| Shot ID | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|
| SH_001 | Establish problem | Medium shot | Eye-level kitchen counter | Natural | Locked-off | Hiker fills a clear glass from cloudy tap water and hesitates | Glass foreground, hiker midground, sink background | Cloudy water is the problem; bottle not shown yet |
| SH_002 | Product reveal | Close-up product shot | Counter-height low angle | Slight telephoto compression | Slow slide right | Bottle is placed beside cloudy glass | Bottle centered, filter window facing camera | Matte charcoal, black cap, blue light off |
| SH_003 | Use action | Medium close-up | Over-hand angle | Natural macro-leaning | Static | Thumb presses cap button; blue light turns on | Hand enters from left, button at upper third | Same bottle orientation; cap attached |
| SH_004 | Proof detail | Extreme close-up insert | Side angle at filter window | Macro feel | Locked-off | Water passes through visible filter window, becoming clear | Filter column fills frame | Blue light on; no magic glow |
| SH_005 | Portability benefit | Wide shot | Low trail-level angle | Wide outdoor feel | Handheld follow | Hiker clips bottle to backpack while walking | Bottle swings in right third, trail recedes | Same bottle; window visible; no second bottle |
| SH_006 | Final packshot | Clean close-up | Eye-level table angle | Slight telephoto | Slow push-in | Bottle stands next to clear glass with condensation | Product centered; glass left; headline space right if needed | Cap black, window front, blue light on |

### 4. Clean Handoff Specs

```yaml
SH_001
scene: modern kitchen sink, problem setup
shot_size: medium shot
camera_angle: eye-level across counter
lens_feel: natural perspective
camera_movement: locked-off
main_subject: hiker holding a clear glass of cloudy tap water
main_action: she pauses before drinking
body_pose: shoulders forward, glass held near mouth, doubtful gaze at water
composition: cloudy glass dominates foreground left; hiker in midground right
foreground: cloudy water glass and counter edge
midground: hiker hand and face
background: faucet, sink, neutral kitchen tiles
scale_reference: normal hand-to-glass scale
continuity_lock: hiker wears olive jacket; product not visible yet
must_preserve: cloudy water readability; hesitation
avoid: dirty horror water, product appearing too early, exaggerated disgust

SH_002
scene: same kitchen counter, product reveal
shot_size: close-up product shot
camera_angle: counter-height low angle
lens_feel: slight telephoto compression
camera_movement: slow slide right
main_subject: matte charcoal refillable purifier bottle
main_action: bottle is placed beside the cloudy glass
body_pose: hand releases bottle from top, fingers leaving cap
composition: bottle centered; cloudy glass left; empty counter space right
foreground: counter texture and water droplets
midground: bottle with translucent vertical filter window facing camera
background: soft sink and tile blur
scale_reference: bottle is taller than glass by one-third
continuity_lock: matte charcoal body, black cap, vertical filter window front, blue status light off
must_preserve: product shape and filter window orientation
avoid: logo hallucination, extra buttons, duplicate bottle, shiny metal finish

SH_003
scene: same counter, activation action
shot_size: medium close-up
camera_angle: over-hand angle looking down at cap
lens_feel: natural macro-leaning
camera_movement: static
main_subject: hand pressing bottle cap button
main_action: thumb depresses button and blue status light turns on
body_pose: thumb centered on button, other fingers wrapping cap
composition: cap button upper third; bottle body drops diagonally through frame
foreground: thumb and cap button
midground: blue status light and bottle shoulder
background: blurred cloudy glass
scale_reference: thumb pad compared to cap button
continuity_lock: same matte charcoal bottle, black cap, filter window front
must_preserve: blue light on after press; single button
avoid: touchscreen interface, floating hologram, extra hand

SH_004
scene: filter proof insert
shot_size: extreme close-up insert
camera_angle: side angle at vertical filter window
lens_feel: macro feel, texture readable
camera_movement: locked-off
main_subject: translucent filter window on bottle
main_action: cloudy water passes downward and appears clear below filter layer
body_pose: no human body visible
composition: filter column fills center; clean water area at bottom third
foreground: tiny condensation droplets on window
midground: filter granules and water line
background: charcoal bottle body edge
scale_reference: droplets show macro scale; filter granules visible but not huge
continuity_lock: same bottle, blue light on, vertical window front
must_preserve: mechanical filtration proof, not magic
avoid: neon liquid, sci-fi beams, unreadable window, open bottle cutaway unless requested

SH_005
scene: outdoor trail, portability benefit
shot_size: wide shot
camera_angle: low trail-level angle
lens_feel: wide outdoor feel
camera_movement: handheld follow
main_subject: hiker clipping bottle to backpack
main_action: bottle swings from side loop as she walks
body_pose: hiker walking left-to-right, right hand releasing clip
composition: bottle in right third, trail leading line to background hills
foreground: gravel and boot step
midground: bottle, backpack side, hiker torso
background: soft green trail and sky
scale_reference: bottle size relative to backpack side pocket
continuity_lock: same matte charcoal bottle, black cap, filter window visible, hiker olive jacket
must_preserve: single product, portable use
avoid: second bottle, mountaineering extreme danger, hidden product

SH_006
scene: final clean table packshot
shot_size: close-up
camera_angle: eye-level table angle
lens_feel: slight telephoto, clean compression
camera_movement: slow push-in
main_subject: purifier bottle standing beside clear glass
main_action: bottle rests upright; clear water glass shows final result
body_pose: no person, product-only end frame
composition: bottle centered; clear glass left; negative space right
foreground: condensation droplets and table reflection
midground: bottle front with filter window and blue light
background: soft neutral kitchen wall
scale_reference: bottle one-third taller than glass
continuity_lock: matte charcoal body, black cap, vertical filter window, blue light on
must_preserve: clear water proof; product orientation
avoid: fake brand text, extra labels, overdesigned sci-fi interface
```

### 5. Why This Shot List Works

- It demonstrates problem, operation, proof, benefit, and end frame in sequence.
- Product continuity is specific enough for AI: body color, cap, window orientation, status light.
- The proof shot is a visual mechanism, not a claim.

### 6. Common Bad Version

```markdown
Show the bottle in a premium cinematic lifestyle ad. Add a hero shot, a user shot, a tech shot, and a final product beauty shot.
```

### 7. Why the Bad Version Fails

- Product features are not visible.
- "Tech shot" does not define a drawable mechanism.
- It does not lock product orientation, color, cap, or light state.
- It may generate unrelated futuristic visuals.

### 8. Readiness for Rough Storyboard Sketch Generator

Ready. Every shot can be sketched, and product continuity is locked from reveal through packshot.

---

## Example 3: Eight-Shot Luxury Skincare Beauty Film

Use case: skincare or beauty ad emphasizing skin, product, tactile action, atmosphere, and graceful progression.

### 1. Input Brief

Create an eight-shot luxury skincare beauty film for a night serum. The ad should feel intimate and tactile, showing skin texture, the amber serum bottle, application, absorption, and calm confidence.

### 2. Creative Constraints

- Product: amber glass serum bottle, white vertical label, gold cap, glass pipette.
- Character: model with short coily hair, warm brown skin, ivory silk robe.
- Preserve natural skin texture; avoid plastic retouching.
- Sequence length: 8 shots.

### 3. Shot List Table

| Shot ID | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|
| SH_001 | Establish private night ritual | Wide shot | Eye-level bathroom doorway | Soft natural | Slow push-in | Model enters frame and approaches vanity | Vanity light line leads to mirror | Same robe, short coily hair, amber bottle already on vanity |
| SH_002 | Product identity reveal | Close-up | Table-height eye-level | Slight telephoto | Locked-off | Hand reaches toward amber bottle | Bottle centered, label facing camera | Gold cap closed, white label front |
| SH_003 | Tactile opening action | Extreme close-up insert | Top three-quarter angle | Macro feel | Static | Fingers twist gold cap and lift pipette | Cap and fingertips fill frame | Bottle remains amber; no spill |
| SH_004 | Serum texture proof | Extreme close-up | Side macro | Macro shallow depth | Locked-off | Drop forms at pipette tip above fingertip | Droplet centered against dark negative space | Droplet half fingernail width |
| SH_005 | Application | Medium close-up | Mirror-adjacent eye-level | Portrait lens feel | Slow slide left | Model touches serum to right cheek | Face on right third; bottle blurred foreground | Cream/serum on right cheek only |
| SH_006 | Skin detail | Close-up | Slight high angle | Macro beauty feel | Locked-off | Fingertips press serum into cheek | Skin texture and fingertip pressure visible | Preserve pores; no plastic skin |
| SH_007 | Human response | Medium shot | Eye-level mirror angle | Soft telephoto | Slow pullback | Model lowers hand, breathes, meets her reflection | Reflection and real face share frame | Same robe, cheek sheen consistent |
| SH_008 | End frame | Product close-up | Low table angle | Telephoto packshot feel | Slow push-in | Bottle and pipette rest beside folded robe sleeve | Product centered, model reflection soft behind | Gold cap, white label, amber glass locked |

### 4. Clean Handoff Specs

```yaml
SH_001
scene: quiet bathroom vanity at night, ritual setup
shot_size: wide shot
camera_angle: eye-level from doorway
lens_feel: soft natural perspective
camera_movement: slow push-in
main_subject: model in ivory silk robe approaching vanity
main_action: she enters and stops at mirror
body_pose: relaxed shoulders, hand touching robe belt, gaze toward vanity
composition: model moves into center; vanity lights form vertical frame
foreground: doorway edge and soft robe sleeve
midground: model and vanity surface
background: mirror, warm wall, amber serum bottle on counter
scale_reference: bottle small but visible on vanity
continuity_lock: short coily hair, warm brown skin, ivory robe, night bathroom, amber bottle on vanity
must_preserve: intimate ritual, not fashion runway
avoid: crowded bathroom, extra products, harsh clinical lighting

SH_002
scene: vanity product reveal
shot_size: close-up
camera_angle: table-height eye-level
lens_feel: slight telephoto compression
camera_movement: locked-off
main_subject: amber glass serum bottle with white vertical label and gold cap
main_action: model's hand reaches toward bottle
body_pose: fingers relaxed, approaching from right side
composition: bottle centered; hand enters from right; mirror blur behind
foreground: marble counter edge
midground: bottle label facing camera
background: soft reflection of model robe
scale_reference: bottle height compared to hand fingers
continuity_lock: amber bottle, white vertical label, gold cap closed
must_preserve: label orientation, amber glass translucency
avoid: unreadable label shape, pump bottle, plastic tube, extra jars

SH_003
scene: cap opening insert
shot_size: extreme close-up insert
camera_angle: top three-quarter angle
lens_feel: macro feel
camera_movement: static
main_subject: fingers twisting gold cap and lifting pipette
main_action: cap separates from bottle neck
body_pose: thumb and index finger pinch cap; other fingers steady bottle
composition: cap at upper third; bottle neck lower center
foreground: fingertip ridges
midground: gold cap and glass pipette
background: amber bottle shoulder
scale_reference: cap diameter compared to fingertip pads
continuity_lock: same amber bottle, gold cap, glass pipette, ivory robe sleeve edge
must_preserve: tactile opening action
avoid: spilled liquid, extra pipettes, nail-art distraction

SH_004
scene: serum droplet proof
shot_size: extreme close-up
camera_angle: side macro angle
lens_feel: shallow macro, dark negative space
camera_movement: locked-off
main_subject: clear-gold serum droplet at pipette tip
main_action: droplet forms above fingertip
body_pose: fingertip held steady below pipette
composition: droplet centered; fingertip lower third; empty dark background
foreground: pipette glass edge
midground: suspended droplet and fingertip
background: dark mirror blur
scale_reference: droplet half the width of fingernail
continuity_lock: same pipette and serum color
must_preserve: droplet shape, fingertip scale, clean negative space
avoid: splash, pearl bead, honey stream, glitter

SH_005
scene: serum application at mirror
shot_size: medium close-up
camera_angle: mirror-adjacent eye-level
lens_feel: portrait lens feel
camera_movement: slow slide left
main_subject: model applying serum to right cheek
main_action: fingertip touches serum to cheek
body_pose: chin slightly lowered, eyes toward mirror, elbow relaxed
composition: face on right third; bottle blurred in lower left foreground
foreground: blurred amber bottle silhouette
midground: model's cheek, hand, robe collar
background: soft mirror and vanity lights
scale_reference: fingertip and cheek contact point visible
continuity_lock: serum on right cheek only, same hair and ivory robe
must_preserve: natural skin texture and gentle touch
avoid: perfect plastic skin, heavy makeup, product disappearing

SH_006
scene: skin texture detail
shot_size: close-up
camera_angle: slight high angle on cheek
lens_feel: macro beauty feel
camera_movement: locked-off
main_subject: fingertips pressing serum into cheek
main_action: small circular press on right cheek
body_pose: fingers softly curved, cheek slightly compressed
composition: cheek fills frame; fingers enter from lower left
foreground: fingertips with serum sheen
midground: skin texture and cheek highlight
background: soft shadow under cheekbone
scale_reference: pores and fingertip ridges visible
continuity_lock: right cheek application, warm brown skin, short coily hair edge
must_preserve: real skin texture, serum sheen
avoid: poreless skin, airbrushed face, exaggerated glow, extra fingers

SH_007
scene: mirror response
shot_size: medium shot
camera_angle: eye-level mirror angle
lens_feel: soft telephoto
camera_movement: slow pullback
main_subject: model looking at her reflection
main_action: she lowers her hand and breathes
body_pose: relaxed shoulders, slight closed-mouth smile, eyes at reflection
composition: real profile left, reflection right, vanity line at bottom
foreground: soft vanity edge
midground: model and reflection
background: warm bathroom wall and mirror lights
scale_reference: normal mirror relationship, same cheek sheen visible
continuity_lock: same ivory robe, right cheek serum sheen, amber bottle on vanity
must_preserve: calm confidence, not exaggerated glamour
avoid: new hairstyle, new outfit, heavy smile, product missing from counter

SH_008
scene: final product end frame
shot_size: product close-up
camera_angle: low table angle
lens_feel: telephoto packshot feel
camera_movement: slow push-in
main_subject: amber serum bottle and glass pipette beside folded robe sleeve
main_action: product rests in final position
body_pose: no person except soft reflection behind
composition: bottle centered; pipette diagonal; model reflection soft in upper background
foreground: marble counter and robe sleeve texture
midground: amber bottle, white vertical label, gold cap
background: soft mirror reflection of model
scale_reference: bottle height compared to folded robe sleeve
continuity_lock: amber glass, white label, gold cap, ivory robe, night vanity
must_preserve: clean final product identity
avoid: fake brand text, extra bottles, unreadable label, harsh sparkle effects
```

### 5. Why This Shot List Works

- It alternates human ritual, product identity, tactile proof, application, and result.
- Skin texture is a concrete visual requirement, not an abstract beauty claim.
- The amber bottle, label, cap, pipette, and cheek application state remain locked.

### 6. Common Bad Version

```markdown
Create an elegant cinematic skincare film with a beautiful woman, glowing skin, luxury lighting, and product close-ups.
```

### 7. Why the Bad Version Fails

- It gives style without shot logic.
- It does not specify which cheek, what bottle state, what texture, or what action.
- "Glowing skin" can erase skin texture and produce plastic retouching.

### 8. Readiness for Rough Storyboard Sketch Generator

Ready. The sequence has distinct storyboard panels and product/character continuity locks.

---

## Example 4: Fifteen-Shot Fast-Cut AI Video Ad

Use case: a 15-second social ad with dense rhythm, visual escalation, and per-shot duration.

### 1. Input Brief

Create a 15-second fast-cut ad for an AI meal-planning app. The app scans a messy fridge and turns it into a simple dinner plan. The video should move from chaos to clarity, with clear rhythm and no abstract software claims.

### 2. Creative Constraints

- Product/UI: phone app named only as `AI meal planner`; no fake brand logo.
- Character: busy young parent in green sweatshirt.
- Core visual motif: messy fridge -> scan -> ingredient cards -> cooking steps -> plated dinner.
- Must include duration per shot.
- Total target duration: 15 seconds.

### 3. Rhythm Structure

| Section | Shots | Duration | Function |
|---|---|---:|---|
| Hook chaos | SH_001-SH_003 | 2.1s | Show the problem fast. |
| AI scan setup | SH_004-SH_006 | 2.4s | Phone enters and captures usable data. |
| Proof burst | SH_007-SH_011 | 4.1s | Convert ingredients into specific steps. |
| Human result | SH_012-SH_013 | 2.2s | Show relief and completed meal. |
| End lock | SH_014-SH_015 | 4.2s | App and dinner resolve together. |

### 4. Shot List Table

| Shot ID | Duration | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---:|---|---|---|---|---|---|---|---|
| SH_001 | 0.7s | Pattern interrupt: fridge chaos | Wide shot | Fridge POV looking out | Wide | Snap zoom out | Parent opens overstuffed fridge | Fridge shelves frame face | Green sweatshirt, messy vegetables |
| SH_002 | 0.7s | Show decision overload | Close-up | Eye-level | Natural | Handheld micro-shake | Parent stares at mismatched leftovers | Face squeezed between fridge items | Same parent, tired expression |
| SH_003 | 0.7s | Insert problem detail | Extreme close-up | Shelf level | Macro | Static | Wilted spinach, half lemon, tofu, carrots crowd shelf | Food items fill frame | Ingredients locked for later cards |
| SH_004 | 0.8s | App enters | Medium close-up | Over-shoulder | Natural phone perspective | Tilt down | Parent raises phone toward fridge | Phone screen lower right, fridge center | Same ingredients visible |
| SH_005 | 0.8s | Scan action | Phone insert | Straight-on | Flat UI readable | Locked-off | Scan frame highlights spinach, tofu, carrots | UI boxes align with ingredients | No fake logo, no unreadable text except simple labels |
| SH_006 | 0.8s | Transformation cue | Close-up | Slight high angle | Clean digital feel | Quick push-in | Ingredient cards stack on phone screen | Cards fan upward | Cards: spinach, tofu, carrot, lemon |
| SH_007 | 0.8s | Proof: recipe output | Phone close-up | Straight-on | Flat readable | Static | App displays "15 min tofu stir-fry" | Recipe title centered, steps below | Keep text short and legible |
| SH_008 | 0.8s | First cooking action | Close-up | Counter height | Natural | Whip cut feel, no camera blur in spec | Tofu cubes hit pan | Pan diagonal, tofu center | Tofu from fridge becomes cooking ingredient |
| SH_009 | 0.8s | Second cooking action | Insert | Top-down | Graphic overhead | Static | Carrot ribbons slide onto cutting board | Orange ribbons form diagonal | Carrot matches card ingredient |
| SH_010 | 0.8s | Third cooking action | Close-up | Side angle | Macro steam feel | Locked-off | Spinach wilts in pan steam | Steam foreground, greens center | Spinach still identifiable |
| SH_011 | 0.9s | Flavor proof | Extreme close-up | Side macro | Crisp macro | Static | Lemon squeezed over pan | Drops arc into frame | Lemon from fridge; no splash chaos |
| SH_012 | 1.1s | Human relief | Medium shot | Eye-level kitchen island | Soft natural | Slow pullback | Parent plates food and smiles lightly | Plate foreground, parent midground | Same green sweatshirt |
| SH_013 | 1.1s | Family proof | Wide shot | Table height | Warm natural | Locked-off | Child reaches for plate; parent sets bowl down | Hands and plates create triangle | Dinner is same tofu/greens/carrot dish |
| SH_014 | 2.0s | Product/app end lock | Close-up | Table angle | Slight telephoto | Slow push-in | Phone beside plated dinner shows recipe completed | Phone left, dish right | App UI readable; no fake logo |
| SH_015 | 2.2s | Final clarity image | Overhead wide | Top-down | Graphic clean | Static | Dinner, phone, remaining ingredients arranged neatly | Clean grid composition | Shows chaos resolved into meal plan |

### 5. Clean Handoff Specs

```yaml
SH_001
scene: kitchen, fridge chaos hook
shot_size: wide shot
camera_angle: fridge POV looking outward
lens_feel: wide feel, shelves close to lens
camera_movement: snap zoom out
main_subject: busy young parent in green sweatshirt opening packed fridge
main_action: fridge door opens to reveal crowded shelves
body_pose: parent leans forward, eyebrows raised, hand gripping door
composition: fridge shelves form frame-within-frame around parent face
foreground: milk carton edge, leafy greens, container lids
midground: parent's face and hand
background: kitchen behind parent
scale_reference: normal hand-to-fridge scale
continuity_lock: green sweatshirt, messy fridge with spinach, tofu, carrots, lemon
must_preserve: visual chaos and ingredient visibility
avoid: brand logos, rotten food horror, empty fridge

SH_002
scene: same fridge, decision overload
shot_size: close-up
camera_angle: eye-level from inside fridge
lens_feel: natural close perspective
camera_movement: handheld micro-shake
main_subject: parent's tired face between fridge items
main_action: parent scans shelves without deciding
body_pose: eyes moving left, mouth tense, shoulders close to fridge
composition: face squeezed between containers left and greens right
foreground: blurred leftover container and carrot bag
midground: face and fridge light
background: kitchen blur
scale_reference: face close to shelf items
continuity_lock: same parent, green sweatshirt, same ingredient mess
must_preserve: overwhelm
avoid: comic panic, new character, missing ingredients

SH_003
scene: fridge shelf problem insert
shot_size: extreme close-up
camera_angle: shelf-level
lens_feel: macro
camera_movement: static
main_subject: mismatched ingredients on shelf
main_action: wilted spinach, half lemon, tofu pack, and carrots crowd the frame
body_pose: no person visible
composition: ingredients layered tightly, no clean empty space
foreground: lemon half and spinach edge
midground: tofu pack and carrots
background: fridge shelf back wall
scale_reference: normal grocery item scale
continuity_lock: spinach, tofu, carrots, lemon must become later recipe ingredients
must_preserve: ingredient identities
avoid: adding meat, replacing tofu, unreadable food shapes

SH_004
scene: app enters fridge scene
shot_size: medium close-up
camera_angle: over-shoulder behind parent
lens_feel: natural phone perspective
camera_movement: tilt down to phone
main_subject: phone raised toward fridge
main_action: parent starts scanning fridge contents
body_pose: right hand holds phone steady; left hand keeps fridge open
composition: phone lower right, fridge contents center
foreground: shoulder and phone edge
midground: phone screen and fridge shelf
background: fridge interior
scale_reference: phone size relative to hand
continuity_lock: same green sweatshirt and same visible ingredients
must_preserve: phone scanning real ingredients
avoid: hologram floating outside phone, unreadable glare

SH_005
scene: phone scan insert
shot_size: phone insert
camera_angle: straight-on to screen
lens_feel: flat UI readable
camera_movement: locked-off
main_subject: phone screen scanning fridge
main_action: simple boxes highlight spinach, tofu, carrots, lemon
body_pose: hand grips phone edges
composition: phone screen fills frame; highlighted boxes align with food behind
foreground: phone bezel and fingers
midground: screen UI boxes
background: blurred fridge contents
scale_reference: phone screen fills most frame
continuity_lock: no fake brand; labels only for spinach, tofu, carrot, lemon
must_preserve: readable scan relationship
avoid: dense tiny UI, fake app logo, unrelated ingredients

SH_006
scene: ingredient cards generated
shot_size: close-up
camera_angle: slight high angle on phone
lens_feel: clean digital feel
camera_movement: quick push-in
main_subject: ingredient cards on phone screen
main_action: cards stack upward: spinach, tofu, carrot, lemon
body_pose: thumb hovers near lower screen
composition: card stack diagonal from lower left to upper right
foreground: thumb and phone edge
midground: four ingredient cards
background: fridge blur
scale_reference: cards sized large enough to read
continuity_lock: same four ingredients
must_preserve: short readable labels
avoid: long paragraphs, fake brand name, too many cards

SH_007
scene: recipe proof on phone
shot_size: phone close-up
camera_angle: straight-on
lens_feel: flat readable
camera_movement: static
main_subject: AI meal planner recipe output
main_action: screen shows "15 min tofu stir-fry" with three short steps
body_pose: hand holds phone still
composition: title centered; step list below; ingredients icons along bottom
foreground: phone bezel
midground: recipe title and steps
background: kitchen blur
scale_reference: readable text size
continuity_lock: no fake logo, recipe uses spinach, tofu, carrot, lemon
must_preserve: simple dinner plan
avoid: tiny unreadable UI, unrelated recipe, claims about health

SH_008
scene: cooking action one
shot_size: close-up
camera_angle: counter-height side angle
lens_feel: natural kitchen close-up
camera_movement: whip cut feel, frame itself readable
main_subject: tofu cubes landing in pan
main_action: tofu cubes scatter into hot pan
body_pose: hand tipping bowl from upper left
composition: pan diagonal across frame; tofu center impact point
foreground: pan rim
midground: tofu cubes
background: stove blur
scale_reference: tofu cubes normal bite size
continuity_lock: tofu from scanned ingredients
must_preserve: tofu identity
avoid: meat cubes, deep fryer, excessive flames

SH_009
scene: cooking action two
shot_size: insert
camera_angle: top-down over cutting board
lens_feel: graphic overhead
camera_movement: static
main_subject: carrot ribbons on cutting board
main_action: orange carrot ribbons slide into a neat diagonal pile
body_pose: hand with peeler partially visible at top edge
composition: bright carrot diagonal across neutral board
foreground: peeler edge
midground: carrot ribbons
background: board texture
scale_reference: ribbons compared to hand
continuity_lock: carrots from scanned ingredients
must_preserve: orange carrot clarity
avoid: random vegetables, blood-like colors, cluttered board

SH_010
scene: cooking action three
shot_size: close-up
camera_angle: side angle near pan
lens_feel: macro steam feel
camera_movement: locked-off
main_subject: spinach wilting in pan
main_action: green spinach folds into tofu steam
body_pose: spatula enters from right
composition: spinach center, tofu pieces visible behind
foreground: soft steam
midground: spinach and spatula
background: pan curve
scale_reference: leaves normal cooking size
continuity_lock: spinach and tofu remain identifiable
must_preserve: green color, edible texture
avoid: mush, neon glow, unidentifiable greens

SH_011
scene: flavor proof insert
shot_size: extreme close-up
camera_angle: side macro
lens_feel: crisp macro
camera_movement: static
main_subject: lemon being squeezed over pan
main_action: small drops arc from lemon into food
body_pose: fingers compress lemon half
composition: lemon upper left, droplets crossing center, pan lower right
foreground: lemon rind texture
midground: droplets
background: blurred tofu and greens
scale_reference: droplets compared to lemon wedge
continuity_lock: lemon from scanned ingredients
must_preserve: clean drops, not splash chaos
avoid: sauce bottle, seeds everywhere, unrealistic waterfall

SH_012
scene: plating relief
shot_size: medium shot
camera_angle: eye-level at kitchen island
lens_feel: soft natural
camera_movement: slow pullback
main_subject: parent plating finished stir-fry
main_action: parent places food into bowl and smiles lightly
body_pose: shoulders lowered, small relieved smile, spoon in right hand
composition: plate foreground, parent midground, warm kitchen behind
foreground: bowl with tofu, greens, carrot
midground: parent in green sweatshirt
background: tidy kitchen counter
scale_reference: normal bowl and spoon scale
continuity_lock: same parent, same green sweatshirt, meal uses scanned ingredients
must_preserve: relief through posture
avoid: exaggerated joy, restaurant chef costume, new outfit

SH_013
scene: family dinner proof
shot_size: wide shot
camera_angle: table-height
lens_feel: warm natural
camera_movement: locked-off
main_subject: parent setting bowl on table as child reaches in
main_action: child hand reaches toward finished dinner
body_pose: parent leaning forward, child hand from lower right
composition: hands and bowls form triangle; phone not primary
foreground: child hand and plate edge
midground: parent setting bowl
background: kitchen table and soft chairs
scale_reference: adult and child hand scale
continuity_lock: same dish, same parent sweatshirt
must_preserve: approachable family proof
avoid: too many people, messy table chaos, unrelated dish

SH_014
scene: app and dinner end lock
shot_size: close-up
camera_angle: table angle
lens_feel: slight telephoto
camera_movement: slow push-in
main_subject: phone beside plated dinner
main_action: app screen shows recipe completed next to finished bowl
body_pose: no person except hand edge leaving frame
composition: phone left, dish right, spoon diagonal between them
foreground: table texture and spoon
midground: phone UI and finished tofu stir-fry
background: soft kitchen lights
scale_reference: phone size compared to bowl
continuity_lock: no fake logo; same tofu, spinach, carrot, lemon dish
must_preserve: resolved chaos-to-meal connection
avoid: dense UI, brand logo, unrelated food, perfect stock-photo sterility

SH_015
scene: final clarity overhead
shot_size: overhead wide
camera_angle: top-down
lens_feel: graphic clean
camera_movement: static
main_subject: finished dinner, phone, and remaining ingredients in neat arrangement
main_action: final organized layout shows meal plan completed
body_pose: no person visible
composition: grid layout: phone upper left, bowl center, remaining lemon/carrot/spinach corners
foreground: none, flat lay
midground: all objects on table plane
background: clean tabletop
scale_reference: bowl, phone, ingredients at normal tabletop scale
continuity_lock: same ingredients, same app, no fake brand
must_preserve: clarity, simplicity, completed meal
avoid: text overload, added logo, too many props, unrelated dishes
```

### 6. Why This Shot List Works

- The rhythm is segmented: chaos, scan, proof, cooking, result, end lock.
- Each fast cut has one visual job.
- Ingredients introduced in the fridge reappear as recipe cards and cooking steps.
- The UI is kept readable by limiting text.

### 7. Common Bad Version

```markdown
Make a fast cinematic AI app ad with lots of quick shots, futuristic UI, happy family, cooking, and a final app screen.
```

### 8. Why the Bad Version Fails

- It offers speed but no rhythm architecture.
- "Futuristic UI" risks fake holograms and unreadable interfaces.
- It does not prove the AI transformed specific ingredients into dinner.
- It does not preserve character or ingredient continuity.

### 9. Readiness for Rough Storyboard Sketch Generator

Ready. The shot durations, section logic, and per-shot handoff specs make it suitable for rough storyboard panels and later animatic timing.

---

## Example 5: Reference-Image-to-Shot-List Example

Use case: converting a single reference image into a structured shot list and clean handoff specs.

### 1. Input Brief

Reference image description: a vertical photo shows a young woman in a red raincoat standing alone under a transparent umbrella at night. She is on the right third of the frame. Neon signs reflect in wet pavement. A blurred tram passes in the background from left to right. The user wants a four-shot storyboard sequence that preserves the reference mood but adds a small narrative beat: she notices a glowing paper crane on the sidewalk.

### 2. Creative Constraints

- Do not copy the reference image as a static poster for every shot.
- Preserve the red raincoat, transparent umbrella, night rain, wet pavement, and tram direction.
- Add the paper crane as the narrative object.
- Maintain vertical 9:16 framing logic.
- Convert observed reference facts into shot specs, then derive motivated alternate shots.

### 3. Reference Image Extraction

- Visible subject: young woman, red raincoat, transparent umbrella.
- Shot size: full shot / wide portrait frame.
- Camera angle: eye-level street view.
- Lens feel: slight telephoto compression; neon reflections layered behind subject.
- Composition: subject on right third; large negative space on left with tram blur.
- Foreground: wet pavement reflections.
- Midground: woman and umbrella.
- Background: neon signs and tram moving left-to-right.
- Pose: standing still, head slightly turned toward street.
- Scale relationship: normal human scale; umbrella roughly shoulder width.
- Continuity to preserve: red raincoat, transparent umbrella, night rain, wet reflections, tram left-to-right.
- Elements to reinterpret: glowing paper crane is added; camera can move closer or lower in derived shots.

### 4. Shot List Table

| Shot ID | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action | Composition | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|
| SH_001 | Anchor shot close to reference image | Full shot in 9:16 | Eye-level street view | Slight telephoto compression | Locked-off | Woman stands under umbrella as tram blurs behind | Subject right third, tram blur left | Red coat, transparent umbrella, wet pavement, tram left-to-right |
| SH_002 | Introduce narrative object | Low insert | Pavement-level looking across sidewalk | Macro/low wide | Static | Glowing paper crane sits in rainwater near her boot | Crane foreground, red boot edge midground | Crane smaller than boot; rain reflections |
| SH_003 | Reaction and discovery | Medium close-up | Slight low angle under umbrella | Portrait lens feel | Slow push-in | She looks down through transparent umbrella rim | Face framed by umbrella ribs | Same red coat, wet hair edge, crane glow reflected |
| SH_004 | Payoff with spatial relation | High angle wide portrait | Looking down from awning | Slight wide | Slow pullback | She crouches to pick up crane while tram passes behind | Woman and crane centered lower frame; tram streak top | Crane in hand, tram still left-to-right |

### 5. Clean Handoff Specs

```yaml
SH_001
scene: rainy neon street at night, reference-anchor shot
shot_size: full shot in vertical 9:16 frame
camera_angle: eye-level street view
lens_feel: slight telephoto compression with layered neon reflections
camera_movement: locked-off
main_subject: young woman in red raincoat holding transparent umbrella
main_action: she stands alone as a tram blurs behind her
body_pose: still, weight on right leg, head slightly turned toward street
composition: subject on right third; tram blur and neon negative space on left
foreground: wet pavement reflections
midground: woman, umbrella, red raincoat
background: neon signs and tram moving left-to-right
scale_reference: normal human scale; umbrella shoulder-width
continuity_lock: red raincoat, transparent umbrella, night rain, wet pavement, tram left-to-right
must_preserve: reference composition and mood anchor
avoid: changing coat color, opaque umbrella, daylight, dry street

SH_002
scene: same sidewalk, discovery insert
shot_size: low insert
camera_angle: pavement-level looking across sidewalk
lens_feel: macro/low wide feel
camera_movement: static
main_subject: small glowing paper crane in rainwater
main_action: crane rests near the woman's red boot
body_pose: only boot edge visible, toe angled toward crane
composition: crane foreground center; boot edge midground right; reflection line leads back
foreground: glowing paper crane and raindrops
midground: red boot edge and puddle ripple
background: soft neon reflection streaks
scale_reference: crane smaller than the width of her boot
continuity_lock: same rain, red coat/boot color, wet pavement
must_preserve: crane as small delicate object
avoid: crane becoming bird, large origami sculpture, dry paper with no rain context

SH_003
scene: under transparent umbrella, reaction
shot_size: medium close-up
camera_angle: slight low angle under umbrella rim
lens_feel: portrait lens feel
camera_movement: slow push-in
main_subject: woman noticing the glowing paper crane below
main_action: she lowers her gaze through the umbrella rim
body_pose: chin lowered, eyes down, one hand gripping umbrella handle
composition: face framed by umbrella ribs; glow reflection touches lower face
foreground: transparent umbrella edge with raindrops
midground: face, hand, red collar
background: soft neon and tram streak
scale_reference: umbrella ribs and face scale normal
continuity_lock: same red raincoat, transparent umbrella, night rain, tram direction implied
must_preserve: quiet discovery, not fear
avoid: open-mouth shock, changed hair/coat, opaque umbrella

SH_004
scene: same street, payoff relation
shot_size: high angle wide portrait
camera_angle: looking down from awning
lens_feel: slight wide feel
camera_movement: slow pullback
main_subject: woman crouching to pick up glowing paper crane
main_action: her fingers reach toward the crane as tram passes behind
body_pose: crouched, umbrella tilted back, left hand extended to ground
composition: woman and crane lower center; tram streak crosses upper background
foreground: awning edge and rain streaks
midground: woman, umbrella, crane, puddle
background: tram blur moving left-to-right, neon signs
scale_reference: crane fits between two fingers; umbrella wider than shoulders
continuity_lock: red raincoat, transparent umbrella, night rain, wet pavement, tram left-to-right
must_preserve: spatial relation between woman, crane, and tram
avoid: crane flying away, new characters, daylight, horizontal aspect framing
```

### 6. Why This Shot List Works

- It treats the reference image as an anchor, not a cage.
- It separates observed facts from invented narrative additions.
- It keeps composition, wardrobe, rain, and tram direction continuous.
- The new object is introduced with scale and then integrated into reaction/payoff shots.

### 7. Common Bad Version

```markdown
Use the reference image to make four cinematic shots of the same woman in the rain. Add a magical glowing paper crane and keep the same atmosphere.
```

### 8. Why the Bad Version Fails

- It does not say which reference facts matter.
- It may repeat the same composition four times.
- It does not specify the crane's size, position, or narrative function.
- "Same atmosphere" is too vague to preserve rain, tram direction, umbrella, and red coat.

### 9. Readiness for Rough Storyboard Sketch Generator

Ready. The reference image has been decomposed into camera, subject, composition, layers, scale, continuity, and avoid rules.
