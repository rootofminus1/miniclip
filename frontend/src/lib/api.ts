import { API_BASE } from './config';
import { userStore } from './userStore.svelte';

function headers(): Record<string, string> {
	return {
		'Content-Type': 'application/json',
		'x-user-id': userStore.current
	};
}



export async function listUploads(): Promise<any[]> {
	const res = await fetch(`${API_BASE}/uploads`, {
		headers: headers()
	});

	if (!res.ok) throw new Error(`Failed to list uploads: ${res.status}`);

	const data = await res.json();
	return data.uploads ?? [];
}

export async function presignView(s3Key: string): Promise<string> {
	const res = await fetch(
		`${API_BASE}/uploads/presign?key=${encodeURIComponent(s3Key)}`,
		{ headers: headers() }
	);

	if (!res.ok) throw new Error(`Failed to get presigned URL: ${res.status}`);

	const data = await res.json();
	return data.url;
}

async function presignThumbnail(key: string) {
	return await presignView(key);
}




type JobStartResponse = {
	clip_id: string;
	status: string;
};

export async function startJob(
	uploadId: string,
	s3Key: string,
	startSec: number,
	endSec: number
): Promise<JobStartResponse> {
	const res = await fetch(`${API_BASE}/jobs`, {
		method: 'POST',
		headers: headers(),
		body: JSON.stringify({
			upload_id: uploadId,
			s3_key: s3Key,
			start_sec: startSec,
			end_sec: endSec
		})
	});

	if (!res.ok) throw new Error(`Failed to start job: ${res.status}`);

	return res.json();
}

export async function pollJob(clipId: string): Promise<any> {
	console.log("clip_id:", clipId)
	const res = await fetch(`${API_BASE}/jobs/${clipId}`, {
		headers: headers()
	});

	if (!res.ok) throw new Error(`Failed to poll job: ${res.status}`);

	const data = await res.json();
	return data.clip;
}

export async function listClips(uploadId?: string): Promise<any[]> {
	console.log("list clips")
	const url = uploadId
		? `${API_BASE}/clips?upload_id=${encodeURIComponent(uploadId)}`
		: `${API_BASE}/clips`;

	console.log("list clips")
	const res = await fetch(url, {
		headers: headers()
	});
	console.log("list clips")

	if (!res.ok) throw new Error(`Failed to list clips: ${res.status}`);

	console.log("list clips")
	const data = await res.json();
	console.log("list clips json?", data)
	return data.clips ?? [];
}