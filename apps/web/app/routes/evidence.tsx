import { useParams } from 'react-router';
import EvidenceReader from '../evidence/reader';

export default function EvidenceRoute() {
  const { workspaceId = '', snapshotId = '' } = useParams();
  // A new identity gets a fresh reader immediately, before effect cleanup runs.
  return <EvidenceReader key={`${workspaceId}/${snapshotId}`} workspaceId={workspaceId} snapshotId={snapshotId} />;
}
