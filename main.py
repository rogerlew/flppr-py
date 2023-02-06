from __future__ import annotations

import time
import datetime
import random
from collections import Counter

from textual.app import App, ComposeResult
from textual.widgets import Static, Button
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Checkbox
from textual import events
from textual.reactive import reactive
from textual.widget import Widget


def random_state(numbits=4, current_state=None):
    def _random_state(numbits):
        return tuple([bool(random.random() > 0.5) for i in range(numbits)])

    state = _random_state(numbits)
    while state == current_state:
        state = _random_state(numbits)

    return state


def flip_bits(register, cmd):
    _register = list(register)
    for i, (c, b) in enumerate(zip(cmd, register)):
        if int(c):
            _register[i] = not b

    return tuple(_register)


class DigitalIndicator(Widget):
    """Generates a greeting."""

    DEFAULT_CSS = """

    DigitalIndicator {
        border: tall transparent;
        background: $panel;
        height: 3;
        width: 9;
        padding: 0 3;
    }
    
    """

    value = reactive(False)

    def __init__(
        self,
        value: bool = False,
        *,
        animate: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        if value:
            self._reactive_value = value

    def toggle(self) -> None:
        self.value = not self.value

    def render(self) -> str:

        if self.value:
            return f'[turquoise2]■[/turquoise2]'
        else:
            return f'[white]□[/white]'


class StaticFooter(Static):

    DEFAULT_CSS = """
    StaticFooter {
        background: $accent;
        color: $text;
        dock: bottom;
        height: 1;
    }
    StaticFooter > .footer--highlight {    
        background: $accent-darken-1;         
    }

    StaticFooter > .footer--highlight-key {        
        background: $secondary;                
        text-style: bold;         
    }

    StaticFooter > .footer--key {
        text-style: bold;        
        background: $accent-darken-2;        
    }
    """


class QuestionApp(App[str]):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 7;
        grid-gutter: 1;
    }
    
    #title {
        width: 100%;
        height: 100%;
        column-span: 2;
        text-style: bold;
        content-align: center bottom;
    } 

    Static.label {
        width: 100%;
        height: 100%;
        content-align: center bottom;
    } 
    
    Horizontal {
        width: 100%;
        content-align: center middle;
        padding: 0 6;
    }
    
    Button {
        width: 100%;
    }
    """

    numbits = 4
    k = 0
    register = [False for i in range(numbits)]
    target = [False for i in range(numbits)]

    reg_widgets = [DigitalIndicator(b, id=f'reg{i}') for i, b in enumerate(register)]
    tar_widgets = [DigitalIndicator(b, id=f'tar{i}') for i, b in enumerate(target)]
    cmd_widgets = [DigitalIndicator(False, id=f'cmd{i}') for i, b in enumerate(target)]

    key_log = 'key.log'
    execute_log = 'execute.log'
    reset_log = 'reset.log'

    status = StaticFooter()
    score = 0

    trial_time = 600
    t0 = None
    update_timer = None

    target_timeout_function = lambda self: 5
    target_timeout = None
    target_t0 = None
    target_time_widget = Static('', classes='label')

    reward = 1
    commission_penalty = 1
    omission_penalty = 1

    def reset_target(self):
        self.k += 1
        self.target = random_state(self.numbits, current_state=self.register)
        self.target_t0 = time.time()
        self.target_timeout = self.target_timeout_function()
        assert self.target != self.register

        with open(self.reset_log, 'a') as fp:
            fp.write(f'{self.k},{time.time_ns()},{self.register},{self.target}\n')

        for i in range(self.numbits):
            self.tar_widgets[i].value = self.target[i]

    def on_mount(self):
        self.register = random_state(self.numbits)
        self.reset_target()

        self.t0 = time.time()
        self.update_timer = self.set_interval(1, self.status_update)

    def status_update(self):
        if self.target_timeout is not None:
            elapsed_target = time.time() - self.target_t0
            if elapsed_target > self.target_timeout:
                self.reset_target()
                self.score -= self.omission_penalty

            elapsed_target = time.time() - self.target_t0
            remaining_target = round(self.target_timeout - elapsed_target)
            if remaining_target >= 0:
                self.target_time_widget.update(f'{remaining_target} s')

        elapsed = time.time() - self.t0
        remaining = datetime.timedelta(seconds=round(self.trial_time - elapsed))
        self.status.update(f'[{remaining}] Score: {self.score}')

        if elapsed > self.trial_time:
            self.exit()

    def compose(self) -> ComposeResult:

        yield Static("Electromechanical Relay Control", id="title")

        yield Static("Current State", classes="label")
        yield Static("Target State", classes="label")
        yield Static("", classes="label")
        yield self.target_time_widget
        yield Horizontal(
            *self.reg_widgets
        )
        yield Horizontal(
            *self.tar_widgets
        )
        yield Static("Command", classes="label")
        yield Static("", classes="label")

        yield Horizontal(
            *self.cmd_widgets
        )

        yield self.status

    def log_key_press(self, bit, cmd_value) -> None:
        with open(self.key_log, 'a') as fp:
            if cmd_value:
                fp.write(f'{self.k},{time.time_ns()},{bit},{self.register[bit] != self.target[bit]},{self.register},{self.target}\n')
            else:
                fp.write(f'{self.k},{time.time_ns()},{bit},{self.register[bit] == self.target[bit]},{self.register},{self.target}\n')

    def on_key(self, event: events.Key) -> None:
        bit = None
        if event.key.lower() == 'a':
            bit = 0
        elif event.key.lower() == 's':
            bit = 1
        elif event.key.lower() == 'd':
            bit = 2
        elif event.key.lower() == 'f':
            bit = 3

        if bit is not None:
            self.cmd_widgets[bit].toggle()
            self.log_key_press(bit, self.cmd_widgets[bit].value)
        else:
            self.execute()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.execute()

    @property
    def cmd(self):
        return [w.value for w in self.cmd_widgets]

    def execute(self) -> None:
        self.register = flip_bits(self.register, self.cmd)

        for i in range(self.numbits):
            self.reg_widgets[i].value = self.register[i]

        with open(self.execute_log, 'a') as fp:
            fp.write(f'{self.k},{time.time_ns()},{self.register == self.target},{self.register},{self.target}\n')

        if self.register == self.target:
            self.score += self.reward
            self.reset_target()
        else:
            self.score -= self.commission_penalty

        for i in range(self.numbits):
            self.cmd_widgets[i].value = False

        self.status_update()
        self.refresh(repaint=True, layout=True)


if __name__ == "__main__":

    app = QuestionApp()
    reply = app.run()
    print(reply)
