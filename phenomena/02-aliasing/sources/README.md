# Sources - 02 Aliasing

Verified citations for the engineers layer and the on-screen facts of *Engineering Phenomena 02 · Aliasing*. Numbers 1 to 7 match the Sources list in `../README.md` (details corrected where needed). Numbers 8 to 35 are additions. Each entry has a link and a one-line note of what it supports.

## How this list was checked (read this first)

- Checked in September 2026. Direct page fetches were blocked by the network policy (PubMed, PMC, Crossref, doi.org, the PNAS, ScienceDirect and IEEE Xplore pages, W3C, HSE, CIE, Wikipedia and others all returned "blocked"). **No full text was opened.**
- Every citation was therefore checked against web-search results: records from publishers, PubMed and PMC, Semantic Scholar, ResearchGate, IEEE Xplore, standards bodies and library catalogues. The links below are addresses that appeared in those results, or the standard DOI resolver. They were not opened from here, so click each one once before publication.
- **[C]** means authors, title, venue, volume, pages and year agree in two or more independent records. **[P]** means one record only, or one detail (DOI, issue, date, clause) was not independently seen, or the statement supported comes from a search excerpt and not from the document itself.
- Wording in quotation marks comes from search excerpts. Check it against the document before it goes on screen.
- Wikipedia was used only as a pointer to primary references. It is never cited.

## A. Sources 1 to 7 (same numbers as the piece README)

**1.** C. E. Shannon, "Communication in the presence of noise", *Proceedings of the IRE*, vol. 37, no. 1, pp. 10-21, January 1949. [doi:10.1109/JRPROC.1949.232969](https://doi.org/10.1109/JRPROC.1949.232969)
- Supports: the sampling theorem. Theorem 1: a function with "no frequencies higher than *W*" is completely determined by its ordinates "spaced 1/2*W* seconds apart". Shannon says earlier forms exist (mathematicians, Nyquist, Gabor). [C]

**2.** A. V. Oppenheim and R. W. Schafer, *Discrete-Time Signal Processing*, 3rd edition, Prentice Hall / Pearson, Upper Saddle River NJ, 2010, ISBN 978-0-13-198842-2. [MIT OpenCourseWare companion page](https://ocw.mit.edu/courses/res-6-dtsp-discrete-time-signal-processing/)
- Supports: chapter 4, "Sampling of continuous-time signals" (sampling theorem, aliasing, anti-aliasing prefilter). Section numbers not confirmed. [C]

**3.** D. Purves, J. A. Paydarfar and T. J. Andrews, "The wagon wheel illusion in movies and reality", *Proceedings of the National Academy of Sciences*, vol. 93, no. 8, pp. 3693-3697, 16 April 1996. [doi:10.1073/pnas.93.8.3693](https://doi.org/10.1073/pnas.93.8.3693) (free copy: [PMC39674](https://pmc.ncbi.nlm.nih.gov/articles/PMC39674))
- Supports: wheels look reversed in movies and stroboscopic light, and a similar illusion is reported in continuous light, which the authors read as discrete processing in the brain (one side of the debate). [C]

**4.** K. Kline, A. O. Holcombe and D. M. Eagleman, "Illusory motion reversal is caused by rivalry, not by perceptual snapshots of the visual field", *Vision Research*, vol. 44, no. 23, pp. 2653-2658, October 2004. [doi:10.1016/j.visres.2004.05.030](https://doi.org/10.1016/j.visres.2004.05.030) ([PubMed 15358060](https://pubmed.ncbi.nlm.nih.gov/15358060/))
- Supports: the other side of the debate: the continuous-light illusion is explained by rivalry between motion detectors, not by snapshots. The piece README had "J. S. Kline"; the first author is Keith Kline. [C]

**5.** Health and Safety Executive, *Lighting at work*, HSG38, 2nd edition, HSE Books, 1997, ISBN 978-0-7176-1232-1. [HSE page](https://www.hse.gov.uk/pubns/books/hsg38.htm), [free PDF](https://books.hse.gov.uk/gempdf/hsg38.pdf)
- Supports: lamps on an alternating supply can modulate their light output so that machinery appears stationary or to move differently, which is a workplace hazard (seen in a search excerpt; paragraph number not confirmed). [C]

**6.** IEEE Std 1789-2015, *IEEE Recommended Practices for Modulating Current in High-Brightness LEDs for Mitigating Health Risks to Viewers*, 2015. [doi:10.1109/IEEESTD.2015.7118618](https://doi.org/10.1109/IEEESTD.2015.7118618) ([IEEE Xplore](https://ieeexplore.ieee.org/document/7118618))
- Supports: LED flicker and its health effects; secondary summaries say it lists "apparent slowing or stopping of motion (stroboscopic effect)" among them. Its main subject is health risk, so use Sources 23 and 24 for definitions and measures of the stroboscopic effect. [C for the citation, P for the statement]

**7.** World Wide Web Consortium, *Web Content Accessibility Guidelines (WCAG) 2.2*, W3C Recommendation, 5 October 2023 (updated 12 December 2024), success criterion 2.3.1 "Three Flashes or Below Threshold", level A. [w3.org/TR/WCAG22](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold)
- Supports: "Web pages do not contain anything that flashes more than three times in any one second period, or the flash is below the general flash and red flash thresholds"; the area limit is 0.006 steradian, which is 25 % of any 10 degree visual field. [C]

## B. Additions, sampling theory and practice

**8.** H. Nyquist, "Certain topics in telegraph transmission theory", *Transactions of the AIEE*, vol. 47, no. 2, pp. 617-644, April 1928. [doi:10.1109/T-AIEE.1928.5055024](https://doi.org/10.1109/T-AIEE.1928.5055024) (reprinted in *Proceedings of the IEEE*, vol. 90, no. 2, pp. 280-305, February 2002)
- Supports: the limit of 2*B* independent signals per second in bandwidth *B*, the result behind the name "Nyquist". It is a signalling-rate result, not the sampling theorem itself. [C; reprint details P]

**9.** H. D. Lüke, "The origins of the sampling theorem", *IEEE Communications Magazine*, vol. 37, no. 4, pp. 106-108, April 1999. [doi:10.1109/35.755459](https://doi.org/10.1109/35.755459)
- Supports: why the theorem is also called Whittaker-Kotelnikov-Shannon: several people found it independently. [C]

**10.** W. Kester, *MT-002: What the Nyquist Criterion Means to Your Sampled Data System Design*, Analog Devices tutorial. [analog.com/MT-002](https://www.analog.com/MT-002.html)
- Supports: aliasing in time and frequency, how to specify the anti-aliasing filter, and how oversampling relaxes the filter. [C]

**11.** Analog Devices, *Practical Analog Design Techniques*, section 5, "Undersampling applications". [PDF](https://www.analog.com/media/en/training-seminars/design-handbooks/Practical-Analog-Design-Techniques/Section5.pdf)
- Supports: band-pass signals can be sampled below twice their highest frequency on purpose, so "*f*<sub>s</sub> > 2*f*<sub>max</sub>" is the rule for signals that start at zero frequency. Title seen only. [P]

**12.** Stanford Research Systems, *About FFT Spectrum Analyzers*, Application Note 1. [PDF](https://www.thinksrs.com/downloads/pdfs/applicationnotes/AboutFFTs.pdf)
- Supports: a real instrument: 256 kHz sampling with an analogue filter that cuts everything above 156 kHz by 90 dB, for a 100 kHz span (2.56 times). Seen in a search excerpt. [P]

**13.** Data Physics, "Dynamic signal analysis review, part 3: aliasing" (blog). [link](https://dataphysics.com/blog/dynamic-signal-analysis/dynamic-signal-analysis-review-part-3-aliasing/)
- Supports: the "guard band ratio" of 2.56: sampling rate about 2.56 times the highest frequency of interest, because an ideal filter cannot be built. Vendor note. [P]

**14.** International Telecommunication Union, Recommendation ITU-R BT.709-6, June 2015. [PDF (mirror)](https://glenwing.github.io/docs/ITU-R-BT.709-6.pdf)
- Supports: picture rates 60, 50, 30, 25 and 24 Hz, and those divided by 1.001 for 60, 30 and 24 (59.94, 29.97, 23.976 Hz). [C]

## C. Additions, perception of sampled motion

**15.** D. J. Finlay and P. C. Dodwell, "Speed of apparent motion and the wagon-wheel effect", *Perception & Psychophysics*, vol. 41, no. 1, pp. 29-34, 1987. [doi:10.3758/BF03208210](https://doi.org/10.3758/BF03208210) ([PubMed 3822741](https://pubmed.ncbi.nlm.nih.gov/3822741/))
- Supports: measured apparent speed of a strobe-lit spoked wheel agreed closely with predictions from angular step and interval; also discusses beta motion. [C]

**16.** M. R. W. Dawson, "The how and why of what went where in apparent motion: modeling solutions to the motion correspondence problem", *Psychological Review*, vol. 98, no. 4, pp. 569-603, 1991. [PubMed 1961774](https://pubmed.ncbi.nlm.nih.gov/1961774/)
- Supports: the nearest neighbour principle is one of three constraints (with relative velocity and element integrity) that model how vision matches elements between pictures. It is a strong tendency, not a law. [C]

**17.** S. Ullman, *The Interpretation of Visual Motion*, MIT Press, Cambridge MA, 1979, ISBN 978-0-262-21007-2. [MIT Press](https://mitpress.mit.edu/books/interpretation-visual-motion)
- Supports: the "minimal mapping" theory of correspondence (matches with less distance cost less). Content known from secondary summaries; book not opened. [C for the citation, P for the content]

**18.** A. B. Watson, A. J. Ahumada Jr. and J. E. Farrell, "Window of visibility: a psychophysical theory of fidelity in time-sampled visual motion displays", *Journal of the Optical Society of America A*, vol. 3, no. 3, pp. 300-307, 1986. [JOSA A abstract](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-3-3-300)
- Supports: the viewer modelled as a filter with a "window of visibility", which predicts the sample rate at which sampled motion looks continuous (unwanted aliases outside the window are not seen; the lowest alias is). The last part is my reading of the model. [C]

**19.** T. Andrews and D. Purves, "The wagon-wheel illusion in continuous light", *Trends in Cognitive Sciences*, vol. 9, pp. 261-263, 2005. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1364661305001117), [author PDF](https://www-users.york.ac.uk/~ta505/tics_2005.pdf)
- Supports: the discrete-sampling reading of the continuous-light illusion. Issue number not confirmed. [P]

**20.** K. A. Kline and D. M. Eagleman, "Evidence against the temporal subsampling account of illusory motion reversal", *Journal of Vision*, vol. 8, no. 4, article 13, pp. 1-5, 2008. [doi:10.1167/8.4.13](https://doi.org/10.1167/8.4.13) ([PMC2856842](https://pmc.ncbi.nlm.nih.gov/articles/PMC2856842/))
- Supports: reversals of two overlapping motions often occur separately, which argues against one shared temporal sampling stage. [C]

**21.** R. VanRullen, L. Reddy and C. Koch, "The continuous wagon wheel illusion is associated with changes in electroencephalogram power at about 13 Hz", *Journal of Neuroscience*, vol. 26, no. 2, pp. 502-507, 11 January 2006. [doi:10.1523/JNEUROSCI.4654-05.2006](https://doi.org/10.1523/JNEUROSCI.4654-05.2006)
- Supports: EEG evidence that the continuous illusion goes with activity near 13 Hz, read by the authors as motion perceived in discrete episodes (10 to 15 Hz); contested by Sources 4 and 20. [C]

## D. Additions, lighting and stroboscopic effect

**22.** A. J. Wilkins, I. Nimmo-Smith, A. I. Slater and L. Bedocs, "Fluorescent lighting, headaches and eyestrain", *Lighting Research & Technology*, vol. 21, no. 1, pp. 11-18, 1989. [doi:10.1177/096032718902100102](https://doi.org/10.1177/096032718902100102)
- Supports: a conventional choke-ballast fluorescent tube pulsates with 43 to 49 % modulation at 100 Hz; a 32 kHz electronic ballast cuts the 100 Hz modulation to under 7 %. [C]

**23.** CIE TN 006:2016, *Visual Aspects of Time-Modulated Lighting Systems - Definitions and Measurement Models*, CIE, Vienna. [CIE page](https://cie.co.at/publications/visual-aspects-time-modulated-lighting-systems-definitions-and-measurement-models), [free PDF](https://files.cie.co.at/883_CIE_TN_006-2016.pdf)
- Supports: definitions. Flicker: visual unsteadiness for a static observer in a static environment. Stroboscopic effect: change in motion perception for a static observer in a non-static environment. The lathe case is strictly a stroboscopic effect. [C]

**24.** CEN, EN 12464-1:2021, *Light and lighting - Lighting of work places - Part 1: Indoor work places*, approved 9 May 2021. [catalogue page](https://standards.iteh.ai/catalog/standards/cen/53fc4ff7-e7df-4ebd-a730-0d5f0ea888e0/en-12464-1-2021); trade-press summary: [CIBSE Journal](https://www.cibsejournal.com/technical/work-light-balance-key-changes-to-workplace-lighting-guidance/)
- Supports: the current workplace lighting standard includes criteria to minimise flicker (PstLM, below 80 Hz) and stroboscopic effect (SVM, 80 Hz to about 2 kHz). Clause number and limit values not confirmed; do not quote numbers. [C for the citation, P for the content]

**25.** N. J. Miller et al., "Flicker: a review of temporal light modulation stimulus, responses, and measures", *Lighting Research & Technology*, 2022 (publisher listing shows 2023). [doi:10.1177/14771535211069482](https://doi.org/10.1177/14771535211069482), [free copy (US Department of Energy)](https://www.energy.gov/sites/default/files/2023-05/ssl-miller-etal-2022-LRT-flicker-review-tlm-stimulus-response.pdf)
- Supports: direct flicker effects below about 80 Hz and the stroboscopic effect above 80 Hz are fairly well understood. Four authors; volume and pages not confirmed. [C]

## E. Additions, strobes, timing lights and helicopters

**26.** Monarch Instrument, *Using a stroboscope to measure RPM* (application note). [PDF](https://monarchserver.com/Files/pdf/Strobe%20for%20RPM.pdf)
- Supports: a stroboscope shows a single still image at the rotation rate and also at 1/2, 1/3, 1/4 of it, so start at a high flash rate and go down to the first single image. Vendor note, date not seen. [P]

**27.** "How does a timing light work?", HowStuffWorks. [link](https://auto.howstuffworks.com/timing-light.htm)
- Supports: a timing light flashes each time the number-one spark plug fires, so the crankshaft mark looks still. Popular source. [P]

**28.** J. B. Heywood, *Internal Combustion Engine Fundamentals*, 2nd edition, McGraw-Hill Education, 2018, ISBN 978-1-260-11610-6. [publisher page](https://www.accessengineeringlibrary.com/content/book/9781260116106)
- Supports: a four-stroke engine takes two crankshaft turns per cycle, so a cylinder fires once every two turns. Book not opened. [C for the citation, P for the content]

**29.** Chadwick-Helmuth Company, "Control of rotor blade stroboscopic display", US patent 4,531,408. [Google Patents](https://patents.google.com/patent/US4531408A/en)
- Supports: real helicopter use of aliasing on purpose: a strobe lights reflective targets on the blade tips so the blades appear stationary for tracking. [C for the citation, P for the content]

**30.** Vertical Flight Society, Vertipedia, biography of James Chadwick (Chadwick-Helmuth Vibrex/Strobex track-and-balance systems). [link](https://vertipedia.vtol.org/biographies/getBiography/biographyID/355)
- Supports: the Strobex strobe blade tracker is a standard helicopter tool. Seen in a search excerpt. [P]

**31.** Airbus Helicopters, "Five-bladed H145 receives type certification by EASA", press release, June 2020. [link](https://www.airbus.com/en/newsroom/press-releases/2020-06-five-bladed-h145-receives-type-certification-by-easa); also the [Leonardo AW139 page](https://helicopters.leonardo.com/en/products/aw139) (five-blade main rotor)
- Supports: five-blade main rotors exist on production helicopters, so "5 blades" is realistic. Rotor speeds of named types were not confirmed. [C]

## F. Additions, cameras

**32.** C.-K. Liang, L.-W. Chang and H. H. Chen, "Analysis and compensation of rolling shutter effect", *IEEE Transactions on Image Processing*, vol. 17, no. 8, pp. 1323-1330, August 2008. [doi:10.1109/TIP.2008.925384](https://doi.org/10.1109/TIP.2008.925384) ([PubMed 18632342](https://pubmed.ncbi.nlm.nih.gov/18632342))
- Supports: in a rolling-shutter sensor each scan line is exposed at a different time, so moving objects are geometrically distorted. Volume, pages and DOI match my records but were only seen once with the PubMed entry. [P]

**33.** P. Plait, "Science out an airplane window: the case of the floating stationary disconnected warped propeller blades", Bad Astronomy, SYFY Wire. [link](https://www.syfy.com/syfy-wire/science-out-airplane-window-case-floating-stationary-disconnected-warped-propeller-blades)
- Supports: real phone-video propellers show aliasing and rolling shutter together. Popular science by an astronomer; date not seen. [P]

**34.** "When a camera's frame rate is synced to a helicopter's rotor...", PetaPixel, 4 March 2017. [link](https://petapixel.com/2017/03/04/cameras-frame-rate-synced-helicopters-rotor/)
- Supports: a real video example of helicopter blades looking frozen when the frame rate matches the blade-passing rate. Popular pointer only. [P]

## G. Additions, accessibility

**35.** Recommendation ITU-R BT.1702-2, *Guidance for the reduction of photosensitive epileptic seizures caused by television*, October 2019. [PDF](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-2-201910-S!!PDF-E.pdf); UK broadcast version: [ITC / Ofcom guidance note](https://www.ofcom.org.uk/__data/assets/pdf_file/0021/16248/gn_flash.pdf)
- Supports: the video rule: a harmful flash is a pair of opposite luminance changes of 20 cd/m² or more (darker image below 160 cd/m²), with more than three per second over more than a quarter of the screen area (area figure from an Ofcom summary). [C for the citation, P for the figures]

## Not confirmed (do not cite these yet)

- The paragraph number and exact wording of the stroboscopic passage in HSG38 (PDF blocked).
- Section numbers in Oppenheim and Schafer (only the chapter title was confirmed).
- The clause number and limit values in EN 12464-1:2021. Trade sources mix its limits with the EU ecodesign limits (SVM 0.4 or 0.9), so quote none.
- The numeric limits of IEEE 1789-2015 (for example "0.08 times the frequency"): reported by trade sources, not seen in the standard.
- Main-rotor speeds of named helicopter types. Only a typical range (roughly 200 to 500 rpm) appeared, in forum-level sources.
- A PMID for Purves et al. 1996: two different numbers appeared, so none is given. The DOI and PMC number are enough.
- The original papers by Whittaker (1915) and Kotelnikov (1933), known only through Source 9, and by Korte (1915), seen only on a pointer page.
- The DOI of the 2002 reprint of Nyquist (1928).

## Notes and checks behind the piece

- **Nyquist words.** "Nyquist rate" is 2*f*<sub>max</sub>, a property of the signal. "Nyquist frequency" or "Nyquist limit" is *f*<sub>s</sub>/2, a property of the sampler, and is the sense used in the film. Some textbooks use "Nyquist frequency" for the signal's band limit (I recall this for Oppenheim and Schafer, not re-checked online), so state which one you mean.
- **Attribution.** Say "Nyquist-Shannon" as the usual name, not "Nyquist proved it": earlier forms are by Whittaker and Kotelnikov [9], and Nyquist's 1928 result is about signalling rate [8].
- **Boundary case.** A sine at exactly *f*<sub>s</sub>/2 that starts at zero phase gives samples that are all zero (checked numerically), so *f*<sub>s</sub> > 2*f*<sub>max</sub> is strict.
- **Nearest match.** The rule that vision links each element to the nearest one [16, 17, 15, 18] is a strong tendency with exceptions. Korte's laws describe how the strength of apparent motion depends on distance, timing and intensity, so they are not the source of this rule.
- **Flicker or stroboscopic effect.** At 100 Hz most people do not see flicker, but a moving object can still look stopped. The defined term for that is the stroboscopic effect [23].
- **Exposure blur (calculated).** A box exposure of length *T* scales the contrast of a pattern at frequency *f* by |sin(π*fT*)/(π*fT*)|. For *T* = 1/60 s that is 0.74, 0.69 and 0.64 at 25, 27.5 and 30 Hz. For *T* = 1/30 s it is 0.19, 0.09 and 0 at the same frequencies: the 30 Hz pattern blurs to grey instead of freezing.
- **Flash area (calculated).** Assuming the hook accelerates linearly from 5 to 47 km/h in 15 s and the star wheel is drawn as in `code/engine/ep.js`, the area whose brightness changes between two consecutive pictures peaks near 6 % of the frame for a wheel of radius 400 px and 9 % for 520 px. WCAG's area limit is about 2.8 % of a 1024 × 768 screen (25 % of a 341 × 256 pixel window, taken from W3C's guidance for a 10 degree field). The ITU and Ofcom limit is 25 % of the screen. Run the finished frames through a flash analyser (for example the Harding FPA) before release.
