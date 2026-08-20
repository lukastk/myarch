# Notices and provenance

Myarch's original desktop behavior and machine integrations were extracted from Lukas Kikuchi's `myrig` repository.

The visual direction, semantic theme approach, command/capture workflow design, collapsed information hierarchy, and transaction discipline were informed by [Omarchy](https://github.com/basecamp/omarchy), particularly Omarchy 3.8.4's Waybar and Omarchy 4.0.0's Quickshell desktop. Omarchy is distributed under the MIT License:

> Copyright (c) David Heinemeier Hansson
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions in its license.

Myarch does not vendor Omarchy's full shell or depend on its command/path namespace. Components were implemented around Myarch's existing backends so Pocket 4 and Sesh/dictation behavior remain authoritative.