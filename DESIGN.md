# Design

Fill this in as you go. Your partner, future teammates, and the review bot read it
to learn where your project is headed. Replace each _italic prompt_.

## Target

Steer a little train around a 48×48 rail yard and pick up waiting passengers.
Each passenger adds a carriage, so turns get tighter as the train gets longer.

## Menu choices

Two items from two different groups (see the D4 guide's "The menu" tab).

| Item | Group | Done when (in your words) |
| --- | --- | --- |
| Text-file levels | Language | We can play three yards drawn as text maps. A legend explains the tiles, and we can add a yard without editing the game code. Tests load each map and check that the train has a clear start. |
| Scripted sound effects | Content | Starting a run, picking up a passenger, and crashing each play a distinct sound. A script makes all three sounds, and game signals trigger them. |

## Words we use

Each word your project uses, what it means, and where it lives in code. A few are
already here from the starter; keep them accurate as you change things.

| Word | Meaning | In code |
| --- | --- | --- |
| cell | one square of the grid | `Vector2i` |
| session | one run, from waiting for the first arrow key to crashing | `Session` in `core/session.gd` |
| tick | a step of the rules in which the moving train advances one cell if the way is clear | `Session.tick()`, `Dragon.tick()` |
| tile kind | what a cell is made of, such as `floor` or `wall` | `Board.TILES`, `TILES` in `tools/build_art.py` |
| piece | one model in the kit: head, straight, turn, tail | `Kit.Piece`, `PIECES` in `tools/build_art.py` |
| passenger | a pickup that adds one carriage and one point | `Session.passenger_cell`, `Session.score` |

## Where things live

_Where do the rules live, where does drawing happen, and how does an event get from
one to the other in your project?_

## Adding a tile kind

_The steps a teammate would follow, naming your actual files._

## Patterns, and what they bought us

_Each pattern you used on purpose, where it is, and what it made easier (or harder).
Where a SOLID principle explains why it helped (for example, open/closed: a new tile
kind or powerup is added, not edited in), say which one._

## One idea we carried over

_Pick one idea you used earlier this quarter in TypeScript (for example a Command queue,
a core kept apart from the framework, data-driven content, or a boundary gate) and
describe its transfer at three levels:_

- _**The problem:** what goes wrong without it, in any engine or language._
- _**The practice:** what we do about it, the same here as in our TypeScript Demos._
- _**The mechanism:** how Godot, GDScript, or Blender does it, and what changed from
  TypeScript (what got easier, what got harder, what we had to give up)._

## Sources we relied on

Claims about how Godot or Blender behaves, checked against the documentation for the
versions we run (Godot 4.7, Blender 5.2). Add a row when a decision depends on one.

| Claim | Source (link) | How we checked it |
| --- | --- | --- |
| The unconnected Principled BSDF Base Color is exported as the glTF material's base color. | [Blender 5.2 manual, glTF Base Color](https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html#base-color) | Rebuilt the kit with `deno task art` and checked that Godot imports the red Train Paint (`#b82f35`) on the locomotive. |
