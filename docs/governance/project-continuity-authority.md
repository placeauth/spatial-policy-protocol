# Project Continuity and Authority

**Status:** Draft continuity guidance. This document does not appoint a person,
grant access, transfer intellectual property, delegate Board authority, or
change SPP 0.1. It records the distinction between corporate authority,
technical stewardship, and infrastructure access so an authorized successor can
act without inferring authority from a GitHub account or repository commit.

## Governing boundary

PlaceAuth Foundation, Inc. is a nonmembership Florida not-for-profit
corporation. Its public governance materials state that governance authority
rests with the Board of Directors. The public Board record presently identifies
one Initial Director and one person holding the President, Secretary, and
Treasurer offices. The Bylaws allow one to seven directors, provide that
directors are elected by the Board, and permit Board vacancies to be filled as
allowed by the Bylaws and applicable Florida law. Officers are appointed by the
Board. A majority of directors then in office is a quorum; written Board action
requires consent signed and delivered by all directors entitled to vote.

The Board may establish committees and delegate authority to the extent
permitted by law. Advisory and technical groups have no Board authority unless
the Board expressly delegates it. No delegated SPP standards authority or
technical-maintainer roster is established in the public repository.

Foundation stewardship of PlaceAuth or SPP does not itself transfer pre-existing
intellectual property. Any relevant license or transfer requires a separate
written instrument and appropriate conflict review.

## Authority layers

| Function | Authority required | What the current records establish | What they do not establish |
| --- | --- | --- | --- |
| Ordinary code and documentation maintenance | Technical authorization plus repository access | Contributors may propose small reviewable changes; maintainers should apply the documented review process. | A named maintainer roster or standing merge authority. |
| Ordinary merge | Repository permission exercised by an authorized technical maintainer | The SPP change process permits ordinary maintenance without changing SPP 0.1. | Who currently holds merge permission or how it is granted. |
| Normative SPP change | Foundation-governance approval, plus the SPP normative-change process | Until expressly delegated, approval must occur under Board authority. | A delegated standards body, voting threshold, or Board procedure beyond the Bylaws. |
| Release publication | Authorization to publish plus repository/release access | Releases must distinguish SPP protocol version from package/project version and follow the release process. | The current release operator, approval path, or credentials. |
| GitHub organization administration | Organization-owner or administrator access, exercised under applicable authority | GitHub is used for the public repository and release history. | The current owners, recovery contacts, or access policy. |
| Security contact | Control of the published security channel and an authorized response process | `SECURITY.md` directs sensitive reports to `security@placeauth.org`. | The mailbox operator, backup operator, and recovery path. |
| Website and domain | Control of the relevant hosting, DNS, registrar, and account-recovery channels | Public project materials identify web and governance locations. | Registrar, DNS, hosting, domain-owner, billing, and recovery arrangements. |

Technical authority and infrastructure access are separate. A GitHub
administrator does not gain Board authority from an account role, and a Board
decision does not grant access until the relevant service account actually
assigns it.

## What may be maintained or approved

### Code and ordinary maintenance

An authorized technical maintainer with repository access may propose, review,
test, and merge ordinary editorial, implementation-only, or explicitly
experimental changes in accordance with
[the SPP Technical Change Process](spp-change-process.md). Such work must not
silently alter SPP 0.1 semantics.

This document does not name an authorized maintainer. If the primary technical
maintainer is unavailable, the Foundation must first identify a person with
lawful authority to act for it, then arrange the necessary repository access.

### Normative protocol changes

A normative SPP change must satisfy the process in
[the SPP Technical Change Process](spp-change-process.md): written proposal,
semantic and compatibility analysis, synchronized normative artifacts where
applicable, public and independent technical review where practical, a decision
record, and explicit approval under Foundation governance. Until a formal
delegation is documented, the Board retains that final authority.

### Releases

An authorized release operator may publish an implementation/project release
only after the documented pre-release checks and status review. That authority
does not change SPP's normative version and does not authorize a normative
protocol change. The current release operator and access path are not public
repository facts; they require confirmation before an emergency release.

### Emergency state when the primary maintainer is unavailable

Until authority and access are confirmed, the conservative default is to:

1. preserve repository history, issues, release records, and available account
   evidence without publishing secrets;
2. pause normative changes, releases, credential changes, IP transactions, and
   external representations of authority;
3. continue only clearly reversible, non-normative maintenance when an
   authorized person has the required repository access; and
4. route security reports through the existing published channel without
   publishing report details.

The Board, or a person lawfully acting under Board authority, may assign a
technical maintainer, release operator, or administrator role through the
appropriate corporate action and relevant service access process. Any such
assignment should be recorded in the corporate record book; a public repository
record should state only the information appropriate for public stewardship.

## Minimum continuity actions to arrange now

The following are proposed actions, not executed actions.

| Action | Why it is needed | Type | Existing authority / required action | Professional review |
| --- | --- | --- | --- | --- |
| Establish a Board-capable succession path and maintain current corporate records. | The public record currently identifies one director, creating a corporate single point of failure. | Corporate | The Board manages corporate affairs, elects directors, and may fill vacancies as allowed by law and the Bylaws. Any implementation must follow applicable law. | Florida nonprofit counsel is prudent, especially for vacancy/succession mechanics. |
| Adopt a written Board action identifying who may make ordinary technical, release, and infrastructure-access decisions. | The repository has no documented maintainer, release-operator, or access-owner roster. | Corporate / operational | Board authority; any delegation must be express and legally permitted. | Counsel is prudent for the scope of delegation and record language. |
| Give at least two authorized people recoverable access to required GitHub, domain, hosting, security-mailbox, and financial/corporate-record systems. | Technical work cannot continue if one account or recovery method is unavailable. | Operational / technical | Access is a service-account operation performed by the account owner or administrator under applicable authority. | Professional review is prudent for corporate-record, financial, and domain ownership arrangements. |
| Maintain an offline, access-controlled inventory of accounts, renewal dates, recovery contacts, and escalation instructions. | Website, domain, email, release, and account recovery depend on information absent from Git. | Operational | No public repository authority is needed to maintain a private inventory; ownership and access changes still require authorization. | Counsel or a qualified operations professional is prudent for record handling and continuity design. |
| Calendar patent/IP, corporate filing, tax, domain-renewal, and security-response deadlines with a backup responsible party. | Missed external deadlines may be irreversible even if the code remains available. | Corporate / operational | Corporate records and any IP arrangements must be handled under applicable authority. | IP counsel, corporate counsel, and tax/accounting professionals are prudent as applicable. |
| Document any pre-existing IP license or transfer separately before relying on Foundation control of SPP assets. | Stewardship alone does not transfer founder or contributor IP. | Corporate / legal | The Bylaws require a separate written instrument and conflict review for relevant transactions. | Legal review is prudent and may be necessary. |

## Single-person dependency register

The public records do not identify backup holders for the following functions;
therefore each is a current or unverified single-person dependency until the
Foundation verifies otherwise in its private records:

- Board authority and director continuity;
- technical maintenance and repository merge authority;
- GitHub organization administration and account recovery;
- release publication;
- security mailbox operation;
- DNS, registrar, domain renewal, website hosting, and billing;
- corporate-record custody, banking, financial access, and statutory filings;
- patent/IP deadlines and the underlying ownership or license records; and
- personal account-recovery factors and emergency contacts.

This list identifies continuity risk; it does not state who controls any
account, property, or credential today.

## Private material that must remain off-repository

Do not store passwords, API tokens, private keys, recovery codes, mailbox
contents, personal contact details, banking information, EIN documentation,
executed consents, signatures, individual conflict disclosures, detailed IP
schedules, patent correspondence, account-recovery answers, or private
corporate records in this repository. Keep them in an access-controlled system
with a documented authorized-access and recovery process.

## Founder-independence conclusion

Another authorized maintainer can now determine how to classify and propose a
technical change from the public SPP process. They cannot, from the public
record alone, determine who may exercise Foundation authority, who has GitHub
or infrastructure access, how a sole-director incapacity or vacancy is handled
in practice, or who may act on IP, financial, tax, domain, and security
matters. Those remaining blockers require private corporate records, explicit
authorized assignments, and—in the areas identified above—appropriate
professional review.
