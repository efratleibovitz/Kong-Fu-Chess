# Kong Fu Chess

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![pytest](https://img.shields.io/badge/Tests-pytest-green)
![Coverage](https://img.shields.io/badge/Coverage-HTML%20Report-brightgreen)

Kong Fu Chess is a Python-based chess-style game that combines classic piece movement with a modern, modular architecture. The project demonstrates clean object-oriented design, configurable movement strategies, and a full test-driven development workflow.

## Overview

This project includes:
- board parsing and validation
- movement logic for king, rook, bishop, queen, knight, and pawn
- timed movement and jump mechanics
- pawn promotion and double-step behavior
- unit and integration testing
- HTML-based coverage reporting

## Features at a Glance

- Modular architecture with clear separation between game logic and UI flow
- Configurable movement strategies through JSON-based factory mapping
- Real-time movement behavior with timing and interception rules
- Extensive test coverage with unit and integration suites

## Project Structure

- core/ - game engine, entities, and movement logic
- infrastructure/ - board parsing utilities
- tests/ - unit and integration test suites
- main.py - entry point for the application

## Requirements

- Python 3.10+
- pytest
- pytest-cov

## How to Play

1. Launch the game with Python.
2. Enter a board layout and commands through the input flow.
3. Click or interact with the board to make moves.
4. Watch timed movement, jumps, captures, and promotions unfold in real time.

## Quick Demo

A typical flow looks like this:
- select a piece
- choose a destination
- wait for the movement animation to complete
- enjoy promotion, capture, or jump effects as the game evolves

## Installation

```bash
pip install pytest pytest-cov
```

## Run the Game

```bash
python main.py
```

## Run Tests

```bash
pytest -q
```

## Generate Coverage Report

```bash
pytest --cov=core --cov-report=html
```

The HTML report will be generated in the htmlcov folder.

## Architecture Highlights

The movement system uses a factory pattern with a JSON-based configuration file, which allows new movement strategies to be added without changing core code. This makes the system easier to extend and maintain.

## Status

- Test suite: passing
- Coverage report: available in htmlcov

## Future Improvements

- add a graphical user interface
- expand rule support for additional chess variants
- improve input handling and user experience
