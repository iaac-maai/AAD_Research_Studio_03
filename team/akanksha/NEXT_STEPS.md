# Next steps and what the app does

## The pipeline

The pipeline is built. The model trains next.

The team is working in this order:

1. print markers and keep them in the photo;
2. capture one still frame;
3. run the segmentation model on the server;
4. measure every detection and convert pixels to millimetres;
5. compare bars, ties and hooks with the bending schedule and Eurocode limits;
6. list faults and plain fix instructions;
7. let a person confirm or reject every fault;
8. sign off the face;
9. save the result and checked photo.

The model runs on the server. The phone or browser sends one photo and a schedule; it does not run the model locally.

## Data and mock-up

The project is moving to licensed online data and a fab-lab mock-up instead of filming a real construction site. Full photos and model weights stay outside GitHub. Only small screenshots and deliverables will be committed to the team folder.

The model can be trained from:

- openly licensed rebar-construction data;
- frames labelled from the fab-lab cage;
- synthetic or optional warm-up data only if the licence allows and it improves the held-out score.

## Thursday demo

Version 1 demonstrates one face, one still photo and this scope:

- marker and scale detection;
- model/server inference;
- bar/tie/hook check;
- fix list;
- human confirm/reject review;
- saved result and checked photo.

## Later

Not part of Thursday's demo:

- continuous video review;
- automatic approval or electronic certification;
- multi-face 3D reconstruction;
- automatic detection of cover thickness;
- slab/footing depth stacking;
- trained-model replacement after Diego's model is released;
- complete national-annex/legal validation.
