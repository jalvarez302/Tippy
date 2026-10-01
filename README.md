# Pre-work - *Tippy*

**Tippy** is a tip calculator application for iOS.

Submitted by: **Jose Alvarez Avina**

Time spent: **2** hours spent in total

## User Stories

The following **required** functionality is complete:

* [ ] User can enter a bill amount, choose a tip percentage, and see the tip and total values.

The following **optional** features are implemented:
* [ ] Settings page to change the default tip percentage.
* [ ] UI animations
* [ ] Remembering the bill amount across app restarts (if <10mins)
* [ ] Using locale-specific currency and currency thousands separators.
* [ ] Making sure the keyboard is always visible and the bill amount is always the first responder. This way the user doesn't have to tap anywhere to use this app. Just launch the app and start typing.

The following **additional** features are implemented:

- [ ] List anything else that you can get done to improve the app functionality!

## Video Walkthrough 

Here's a walkthrough of implemented user stories:

<img src='https://gph.is/g/EJg193A' title='Video Walkthrough' width='' alt='Video Walkthrough' />

GIF created with [Giphy](http://www.Giphy.com).

## Notes

Describe any challenges encountered while building the app.

## Terminal Snake

This repo also carries `terminal_loader`, a curses package with two modes.

**Play it**

```
python3 play_snake.py
```

Arrows or WASD steer, `p` pauses, `r` restarts after a crash, `q` quits. You
start at four segments and gain one per pellet. Walls and your own body are
fatal, and the speed steps up every four pellets until it plateaus. Pass
`--wrap` to pass through the walls instead of dying on them, or `--speed N` to
set the starting pace in cells per second.

**Play it while something slow runs**

```
python3 think_snake.py --seconds 60      # timed round
python3 think_snake.py -- npm test       # play while a real command runs
```

One letter of the status word appears at a time, in order. Every letter you
swallow becomes your snake, so the body is the word itself rather than a chain
of circles:

```
Ruminating
```

You start as a single marker and grow into the word. The head carries the first
letter you ate and each new letter is added behind it, so the word reads in
order when you are travelling left. Finish it and the snake holds still for two
seconds so you can read what you spelled, while a glint runs along it the way
it does across Claude Code's status word. Then it heats up and bursts, and the
next word grows out of the spark left where its head was.

The command runs on a background thread. When it finishes, the screen says so
and waits for you to quit, then prints its output and exit code. See
`claude-snake-plugin/` for the plugin shaped around this.

**Watch it**

```
python3 test_snake_loader.py --duration 15
```

The loader drives itself: the snake chases the letters of a status word, eats
them one at a time, and moves on to the next word. Use it as a loading
animation via `SnakeLoader` rather than as a game.

Needs a real terminal at least 34 columns wide, and nothing outside the standard
library.

## License

    Copyright [2020] [Jose Alvarez Avina]

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
