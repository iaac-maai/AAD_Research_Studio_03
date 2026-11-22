# ROI-1555: permission email (task 7)

**Status:** drafted Sun 22 Nov, **not sent yet**. Akshat sends it from his IAAC address.

**To:** Prof. Yi Shao (corresponding author), Shao Lab. The address is on the paper's first page
(Sun, Fan & Shao 2025, *Advanced Engineering Informatics* 65, 103224:
https://www.sciencedirect.com/science/article/pii/S147403462500117X) and on https://www.shao-lab.com.
Cc: Tao Sun (first author), if his address is listed.

**Why:** the dataset card on Hugging Face (`tsrobcvai/ROI-1555_Rebar_Detection_and_Instance_Segmentation_Dataset`)
has no licence, so we may not train on it or publish a model trained on it without asking. It is the best match
that exists for our task (real photos, instance masks of rebar).

---

**Subject:** Permission to use ROI-1555 in a student project (IAAC, Barcelona)

Dear Prof. Shao,

I am a Master's student in Advanced Architecture and AI at IAAC in Barcelona. With two classmates I am building
Concrete Evidence, a student project that checks the rebar of a column from one site photo before the pour
(bar count, spacing, ties and hook angles against the bar bending schedule), with a person confirming every
fault.

Your ROI-1555 dataset is the closest match to our task that we have found, and we read your paper
"Deep learning-based rebar detection and instance segmentation in images" with great interest. The dataset page
on Hugging Face does not state a licence, so before using it we would like to ask your permission to:

1. train a YOLOv8 segmentation model on ROI-1555 together with our own photos, for this non-commercial course
   project (presentation on Thursday 26 November 2026), and
2. publish the trained model weights on Hugging Face (organisation `iaac-maai`) with a model card that cites
   your paper and credits the dataset. We would not redistribute the images themselves.

If you prefer that we only use it internally, or not at all, we will of course follow that. If a specific
licence or wording should go on the model card, please let us know.

Thank you very much for publishing the dataset.

Kind regards,
Akshat Dayal
MaAI 2026, Institute for Advanced Architecture of Catalonia (IAAC), Barcelona

---

**After an answer:** note it in `datasets/CATALOGUE.md` (ROI-1555 row) and tell Diego. Yes → Diego adds it as a
training source; no answer by Mon 23 Nov → we train without it (already the plan).
