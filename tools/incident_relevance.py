"""Conservative incident relevance decisions; source facts are never rewritten."""

STATES = {'ACTIVE', 'HISTORICALLY_RELEVANT', 'INACTIVE', 'EXCLUDED', 'REVIEW_REQUIRED'}


def classify_relevance(record, review=None):
    review = review or {}
    requested = review.get('status')
    if requested:
        if requested not in STATES or not review.get('reason') or not review.get('reviewer'):
            raise ValueError('reviewed relevance requires a valid status, reason and reviewer')
        return {'status': requested, 'reason': review['reason'], 'basis': 'RECORDED_REVIEW',
                'reviewer': review['reviewer'], 'reviewedAt': review.get('reviewedAt')}
    sources = [source for source in record.get('sources', []) if source.get('sourceId') and source.get('url')]
    if not record.get('id') or not sources:
        return {'status': 'REVIEW_REQUIRED', 'reason': 'Traceable source evidence or incident identity is missing.', 'basis': 'DETERMINISTIC'}
    if not (record.get('title') and record.get('summary')):
        return {'status': 'REVIEW_REQUIRED', 'reason': 'The reported event lacks a title or description.', 'basis': 'DETERMINISTIC'}
    if not any(record.get(field) for field in ('system', 'technology', 'aiSystemType')):
        return {'status': 'REVIEW_REQUIRED', 'reason': 'The affected AI system is not sufficiently identified.', 'basis': 'DETERMINISTIC'}
    return {'status': 'ACTIVE', 'reason': 'Traceable source, reported event and affected system are present; substantive claims remain unverified.', 'basis': 'DETERMINISTIC'}
