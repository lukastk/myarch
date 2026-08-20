# GPD Pocket 4 touch/display helpers.
#
# These are the same commands the waybar buttons call — the buttons are just
# click targets for them, so anything you can do from the bar you can do from a
# shell (handy over SSH, or when the bar is hidden in portrait).
#
# The underlying scripts live in home/.mybin/^pocket4^pocket4-*. Note rotation
# always changes the monitor AND touchscreen transform together; doing them
# separately leaves taps landing in the wrong place.

my_alias por='~/.mybin/pocket4-display orientation'	-g pocket -d 'Toggle display landscape <-> portrait (also rotates touch input)'
my_alias pfl='~/.mybin/pocket4-display flip'		-g pocket -d 'Flip the display 180 degrees'
my_alias pds='~/.mybin/pocket4-display get'		-g pocket -d 'Show current orientation (landscape/portrait)'
my_alias ptm='~/.mybin/pocket4-tablet-mode toggle'	-g pocket -d 'Toggle tablet mode (larger touch scale)'
my_alias ptms='~/.mybin/pocket4-tablet-mode get'	-g pocket -d 'Show whether tablet mode is on'
my_alias pkb='~/.mybin/pocket4-osk toggle'		-g pocket -d 'Show/dismiss the on-screen keyboard'
my_alias pkbs='~/.mybin/pocket4-osk get'		-g pocket -d 'Show whether the on-screen keyboard is up'
