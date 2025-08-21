# AI Dungeon Master Product Overview

## What is AI Dungeon Master?

AI Dungeon Master is a Discord bot that serves as an intelligent Dungeon Master for D&D 5.1 campaigns. The bot leverages AI language models to create immersive, interactive tabletop RPG experiences directly within Discord servers.

## Core Features

- **Campaign Management**: Create, join, and manage D&D campaigns within Discord servers
- **Character Management**: Add, update, and track player characters with optional character sheet integration
- **AI-Powered Storytelling**: Uses AI language models (OpenAI, etc.) to generate narrative responses and manage game flow
- **Server Configuration**: Customizable settings for dice roll visibility, character sheet modes, and play styles
- **Persistent Campaign Memory**: Maintains campaign history and world state across sessions

## Architecture

The system follows a modular monolith pattern with three main packages:
- **Bot Package**: Discord interface using discord.py with Cogs pattern
- **Backend Package**: FastAPI service handling AI logic and data persistence
- **Shared Package**: Common models, API client, and utilities

## Target Users

- D&D players and Dungeon Masters looking for AI-assisted gameplay
- Discord communities wanting to run tabletop RPG sessions
- Self-hosting enthusiasts (Docker Compose deployment)