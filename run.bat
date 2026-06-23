@echo off
cd /d "%~dp0"
python train_initial.py
python run.py
