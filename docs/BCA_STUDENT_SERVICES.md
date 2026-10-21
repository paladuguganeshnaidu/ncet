# NCET BCA — Student Services and Project Community

## Routes

| URL | Audience | Indexing |
| --- | --- | --- |
| `/` | Public service landing page | Public, indexable |
| `/students` | Public BCA student-service explanation | Public, indexable |
| `/students/portal` | Signed-in BCA students | Noindex |
| `/bca/manage` | BCA faculty, HOD and administrator | Noindex |
| `/community` | All signed-in NCET members | Noindex, authenticated GET |
| `/app` | Staff/HOD/Principal/IQAC/Admin | Noindex |

**Students and complaints are not indexed.** Student names and USNs appear only
in authenticated collaboration profiles, project posts and shared comments.
There are no direct messages or private chat in the project board.

## Enrollment by BCA faculty

1. Sign in to the faculty workspace with a BCA department account.
2. Open **Student enrollment & requests** or visit `/bca/manage`.
3. Download the CSV template and upload `usn,full_name,semester` headers.
4. Example (illustrative; no sample accounts preloaded):

   ```csv
   usn,full_name,semester
   1NC24BCA001,Student Example,3
   ```

5. Student USNs must begin with `1NC`; maximum 100 rows and 150 KB each CSV.
6. Download and privately distribute generated credentials **once**. Temporary
   passwords are not emailed, retained in plaintext, or logged.
7. Students sign in at `/students/portal` and change passwords before submitting.

## Confidential cases

Students submit categorized academic concerns, requests or complaints. Only the
student and authorized BCA HOD may read case content and send replies. Faculty
can enroll students but cannot read confidential complaints. HOD status actions:
in review, resolved and closed. Status transitions and replies are auditable.

## Project contributions

Students edit a profile (name and USN drawn from verified enrollment), post
projects and specify needed contributors. Anyone signed in with an NCET account
can read the directory, posts and visible comments, including the HOD,
Principal and IQAC. Conversations are in shared threads only.
BCA HOD and administrator can hide inappropriate posts or comments.
Students can change post status; basic rate limits apply.

Do not post private complaints, phone numbers, passwords, addresses or sensitive
personal data on the shared board.

## Production and recovery

- Migration sequence: `6bcabca001`, then `7c9bca002`. These are additive;
  they do not rename existing users, documents or HOD rules.
- Production DB backup and dry-run migration are recommended before merge.
- Set the Render web worker to always-on infrastructure for reliable OCR.
- Arrange institutional privacy approval for display of student names/USNs to
  authenticated members. Establish moderation, retention, password-reset and
  account lifecycle procedures before real enrollment.
- Keep all Render secrets and CSV password files out of public repositories.
- To roll back UI/code, deploy the previous commit. For DB migrations, avoid
  destructive downgrades; leave the additive tables unused until reconciled.
