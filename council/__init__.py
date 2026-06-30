"""Council of models: a development-time design aid.

Never part of the submitted agent. The simulator (gauntlet) is the arbiter;
the council only proposes, cross-critiques, and synthesizes a single spec for a
human to turn into a gauntlet experiment. All API keys are read from environment
variables and never written to disk or logs.
"""
