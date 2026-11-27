GARMENT LINE 3D SIM  -  Kaarkhana-Meta test rig
================================================
HOW TO RUN
  Windows : double-click start.bat   (or open index.html in Chrome / Edge / Firefox)
  Mac/Linux: open index.html in a browser
  No install, no internet needed (Three.js r149 is bundled in js/).

CONTROLS
  PLAY button / Enter / Space  - start (workers only move after this)
  ESC                          - stop, shows "STOP RECORDING" overlay
  R                            - restart
  H                            - hide/show HUD (hide it for clean recording)
  1 / 2 / 3                    - sim speed x1 / x2 / x3

THE LINE (10 stations, flow left -> right, all operators face the last station)
  ST1 Shoulder Join | ST2 Collar Attach | ST3 Placket Make | ST4 Placket Attach
  ST5 Sleeve Attach (slowest / bottleneck, red sign) | ST6 Side Seam | ST7 Sleeve Hem
  ST8 Bottom Hem | ST9 Buttonhole & Button | ST10 Bartack & QC
  Loose, unfolded cut polo pieces are pushed hand-to-hand along the table, so piles
  naturally build up in front of ST5. Cycle times vary, operators stall/pause,
  and arrivals are irregular - it is deliberately not smooth.

TWEAKING  (js/app.js)
  TIMES        - cycle time per station in seconds (index 4 = slow station, see SLOW / NAMES)
  spawn timing - see nextSpawn in updateSim()

RECORDING TIPS
  Camera is fixed at ~35 deg down. Press F11 for fullscreen, H to hide the HUD,
  then screen-record. ESC ends the run.
