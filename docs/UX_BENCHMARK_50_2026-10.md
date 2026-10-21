# NCET VerifyFlow — UX benchmark & release audit (16 October 2026)

## Scope and methodological limits

This is a **public-page-level comparative review** of 50 student service entry points,
not a recursive crawl, source-code audit, usability study, or claim of WCAG
certification for those institutions. The public web browser was used to open
each of the 50 URLs once and read available text and navigation. **37 returned
some usable site content** (three of those returned very limited text or
redirected to a general home page), while **13 were inaccessible to this
browser**. Do not interpret inaccessible as down, insecure, or broken.

Only broad patterns can be inferred from publicly visible experiences.
Private portals cannot be evaluated without legitimate access.

## Actionable patterns observed

| Reference | Public observation | NCET change |
|---|---|---|
| [Cornell Student Essentials](https://studentessentials.cornell.edu/) | Task-based Personal / Academic / Community sections and quick searches | Three real service entry points with clear action labels and quick USN search |
| [Yale Hub](https://yub.yale.edu/) | Relevant authenticated tasks, calendar and to-dos in one place | Do not overload public page; keep actions linked to authenticated role areas |
| [UC Berkeley Students](https://www.berkeley.edu/students/) | Distinct student services and actual named systems rather than generic marketing | Link labels describe the action and destination |
| [Monash Current Students](https://www.monash.edu/students) | First-step guidance, service finder, support and complaint pathways | Add native accessible getting-started questions and student-service links |
| [UNSW Current Students](https://www.unsw.edu.au/student) | Help search plus complaints and student-support resources | Public BCA profile search and identifiable complaint entry point |
| [University of Melbourne](https://students.unimelb.edu.au/) | Featured essential tasks, popular pages and help section | Emphasize useful tasks and keep core navigation compact |
| [University of Southampton Student Hub](https://www.southampton.ac.uk/studentservices/) | Central student help and service routing | Remove disconnected demo-style visuals |
| [NUS Office of Student Affairs](https://www.nus.edu.sg/osa/) | Services grouped under support, resources, community | Preserve separate private requests and authenticated community |
| [Cornell / UK DfE / GOV.UK guidance](https://design-system.service.gov.uk/accessibility/) | Keyboard access, visible focus, sensible feedback and consistent components are critical | Reinforce focus styles, reduced-motion, loading, and field feedback |

## Prioritized observations in NCET source before work

1. **High: confusing hero animation.** Rotating Guidance/Connection/Progress words
   and numbered cards projected an unfinished prototype. Replaced by a
   static institutional identity composition and useful linked actions.
2. **High: public copy contradicted data policy.** Public page stated student
   names could never be indexed, although students can opt in to a
   public profile. Corrected copy to distinguish confidential complaints
   from voluntary public profiles.
3. **Medium: faculty enrollment had no fast roster search or safe export.**
   Added in-page USN/name filter, live count and a no-password export.
4. **Medium: directory loading unclear and rapid searches could race.**
   Added visible loading skeletons, `aria-busy` state and response ordering.
5. **Medium: inconsistent responsive visual polish.** Added one shared
   experience stylesheet and separate authenticated-workspace polish,
   retaining the existing navy/orange brand system.
6. **Medium: keyboard discoverability and motion.** Added skip navigation,
   visible focus states, native FAQ details and a reduced-motion policy.

## Inventory of the 50 attempted student-service sites

| # | Institution / public entry point | Access result |
|---:|---|---|
| 1 | [Yale Hub](https://yub.yale.edu/) | Limited text |
| 2 | [UC Berkeley](https://www.berkeley.edu/students/) | Readable |
| 3 | [Monash University](https://www.monash.edu/students) | Readable |
| 4 | [Stanford Student Services](https://studentservices.stanford.edu/) | Readable |
| 5 | [Oxford University](https://www.ox.ac.uk/students) | Readable |
| 6 | [MIT Student Life](https://studentlife.mit.edu/) | Readable |
| 7 | [Harvard College](https://college.harvard.edu/student-life) | Readable |
| 8 | [Cambridge University](https://www.cam.ac.uk/students) | Not accessible |
| 9 | [UCL](https://www.ucl.ac.uk/students) | Readable |
| 10 | [Imperial College](https://www.imperial.ac.uk/students/) | Not accessible |
| 11 | [University of Edinburgh](https://www.ed.ac.uk/studying/current-students) | Not accessible |
| 12 | [University of Manchester](https://www.manchester.ac.uk/study/) | Readable |
| 13 | [University of Warwick](https://warwick.ac.uk/students/) | Readable |
| 14 | [Durham University](https://www.durham.ac.uk/study/) | Not accessible |
| 15 | [King's College London](https://www.kcl.ac.uk/study) | Readable |
| 16 | [University of Bristol](https://www.bristol.ac.uk/students/) | Readable |
| 17 | [University of Glasgow](https://www.gla.ac.uk/students/) | Not accessible |
| 18 | [University of Nottingham](https://www.nottingham.ac.uk/studentservices/) | Readable |
| 19 | [University of Southampton](https://www.southampton.ac.uk/studentservices/) | Readable |
| 20 | [University of Exeter](https://www.exeter.ac.uk/students/) | Readable |
| 21 | [National University of Singapore](https://www.nus.edu.sg/osa/) | Readable |
| 22 | [Nanyang Technological University](https://www.ntu.edu.sg/life-at-ntu/student-life) | Readable |
| 23 | [University of Hong Kong](https://www.cedars.hku.hk/) | Readable |
| 24 | [HKUST](https://osa.ust.hk/) | Not accessible |
| 25 | [University of Toronto](https://studentlife.utoronto.ca/) | Readable |
| 26 | [McGill University](https://www.mcgill.ca/students) | Not accessible |
| 27 | [University of British Columbia](https://students.ubc.ca/) | Not accessible |
| 28 | [University of Waterloo](https://uwaterloo.ca/student-success/) | Readable |
| 29 | [Western University](https://studentservices.uwo.ca/) | Limited text |
| 30 | [University of Alberta](https://www.ualberta.ca/en/current-students/index.html) | Limited text |
| 31 | [UNSW Sydney](https://www.unsw.edu.au/student) | Readable |
| 32 | [University of Melbourne](https://students.unimelb.edu.au/) | Readable |
| 33 | [University of Sydney](https://www.sydney.edu.au/students.html) | Not accessible |
| 34 | [Australian National University](https://www.anu.edu.au/students) | Readable |
| 35 | [University of Queensland](https://my.uq.edu.au/) | Readable |
| 36 | [RMIT University](https://www.rmit.edu.au/students) | Readable |
| 37 | [Deakin University](https://www.deakin.edu.au/students) | Readable |
| 38 | [Curtin University](https://www.curtin.edu.au/students/) | Readable |
| 39 | [University of Western Australia](https://www.uwa.edu.au/students) | Readable |
| 40 | [University of Auckland](https://www.auckland.ac.nz/en/students.html) | Readable |
| 41 | [University of Otago](https://www.otago.ac.nz/students) | Not accessible |
| 42 | [Victoria University of Wellington](https://www.wgtn.ac.nz/students) | Not accessible |
| 43 | [Cornell Student Essentials](https://studentessentials.cornell.edu/) | Readable |
| 44 | [Princeton University](https://odoc.princeton.edu/) | Readable |
| 45 | [Dartmouth College](https://students.dartmouth.edu/) | Redirected to general homepage |
| 46 | [Brown University](https://www.brown.edu/campus-life) | Readable |
| 47 | [Columbia University](https://www.columbia.edu/students) | Not accessible |
| 48 | [New York University](https://www.nyu.edu/students.html) | Not accessible |
| 49 | [Northwestern University](https://www.northwestern.edu/studentaffairs/) | Readable |
| 50 | [University of Michigan](https://campusinfo.umich.edu/) | Readable |

## Scope deliberately not expanded

No unrelated college marketing, admission pages, invented institutional
statistics, public confidential records, unsupported attendance integrations,
new database tables or additional AI data sharing.

## Release verification protocol

- GitHub CI: full Python regression, migrations and drift, Node syntax, Chromium.
- Chromium: five roles, BCA/Task/Community pages, 320/390/768/1024/1440 widths,
  keyboard FAQ navigation and signed-in roster search/export with mocked API.
- After deployment: exact commit Live; observe startup and real HTTP 200 for
  public routes and protected route 401/403 without credentials.
- Distinguish automated browser-mock checks from an authenticated live workflow.
- **No numerical Lighthouse scores or WCAG certification is asserted unless measured.**
