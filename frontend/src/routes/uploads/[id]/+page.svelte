<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { presignView, startJob, pollJob, listClips } from '$lib/api';
	import { CLIPS_CDN } from '$lib/config';


	const POLL_INTERVAL_MS = 2000;

	type Clip = {
		clip_id: string;
		status: string;
		output_key?: string;
		start_sec: number;
		end_sec: number;
		created_at: string;
	};


	const uploadId = $derived($page.params.id);
	const filename = $derived($page.url.searchParams.get('filename') || uploadId);
	const s3Key = $derived($page.url.searchParams.get('key') || '');

	let videoUrl = $state<string | null>(null);
	let videoError = $state<string | null>(null);
	let loadingVideo = $state(true);

	let startSec = $state('');
	let endSec = $state('');
	let clipping = $state(false);
	let clipStatus = $state<any>(null);
	let clipError = $state<string | null>(null);

	let clips = $state<Clip[]>([]);
	let loadingClips = $state(true);

	let pollInterval: ReturnType<typeof setInterval> | null = null;


	onMount(async () => {
		try {
			if (!s3Key) throw new Error('No s3 key provided.');
			videoUrl = await presignView(s3Key);
		} catch (e: any) {
			videoError = e.message;
		} finally {
			loadingVideo = false;
		}

		try {
			const raw = await listClips(uploadId);
			clips = raw
				.map((c: any) => ({ ...c, clip_id: c.clip_id ?? c.pk }))
				.filter((c: Clip) => c.status !== "failed")
				.sort((a: Clip, b: Clip) =>
					new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			);
		} finally {
			loadingClips = false;
		}
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});


	async function handleClip() {
		const s = parseFloat(startSec);
		const e = parseFloat(endSec);

		if (isNaN(s) || isNaN(e) || s >= e) {
			clipError = 'Invalid times';
			return;
		}

		clipping = true;
		clipError = null;

		try {
			const job = await startJob(uploadId, s3Key, s, e);
			clipStatus = job;

			pollInterval = setInterval(async () => {
				const clip = await pollJob(job.clip_id);
        console.log(clip.status)
				clipStatus = clip;

				if (clip.status === 'done' || clip.status === 'failed') {
					clearInterval(pollInterval!);
					pollInterval = null;
					clipping = false;

					if (clip.status === 'done') {
						clips = [clip, ...clips];
					}
				}
			}, POLL_INTERVAL_MS);
		} catch (e: any) {
			clipError = e.message;
			clipping = false;
		}
	}

	function clipLink(key: string) {
		return `${CLIPS_CDN}/${key}`;
	}
</script>

<p><a href="/uploads">← back to uploads</a></p>

<h2>Upload: {filename}</h2>

{#if loadingVideo}
  	<p>Loading video...</p>
{:else if videoError}
  	<p style="color: red">Error: {videoError}</p>
{:else}
  	<video src={videoUrl} controls style="max-width: 700px; width: 100%; display: block;"></video>
{/if}

<hr>

<h3>Create a clip</h3>

<div style="display: flex; flex-direction: column; gap: 0.5rem; max-width: 400px;">
	<label>
		Start (seconds):
		<input type="number" min="0" step="0.1" bind:value={startSec} disabled={clipping} />
	</label>
	<label>
		End (seconds):
		<input type="number" min="0" step="0.1" bind:value={endSec} disabled={clipping} />
	</label>
	<div>
		<button onclick={handleClip} disabled={clipping || !videoUrl}>
		{clipping ? 'Clipping...' : 'Clip it!'}
		</button>
	</div>

	{#if clipError}
		<p style="color: red">{clipError}</p>
	{/if}

	{#if clipStatus}
		<p>
		Status: <strong>{clipStatus.status}</strong>
		</p>
	{/if}
</div>

<hr>

<h3>Clips for this upload</h3>

{#if loadingClips}
  	<p>Loading clips...</p>
{:else if clips.length === 0}
  	<p>No clips yet.</p>
{:else}
	<ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.75rem;">
		{#each clips as clip}
			<li style="display: flex; align-items: center; gap: 1rem;">
				<video
					src={clipLink(clip.output_key)}
					controls
					preload="metadata"
					style="width: 360px; object-fit: cover; flex-shrink: 0;"
				/>
				<div>
				<div style="font-size: 0.875rem; color: #555;">
					{clip.start_sec}s - {clip.end_sec}s
					&nbsp;·&nbsp; {new Date(clip.created_at).toLocaleString()}
				</div>
				<div>status: <strong>{clip.status}</strong></div>
					{#if clip.status === 'done' && clip.output_key}
						<div>
						<a href={clipLink(clip.clip_id)} target="_blank">link to clip</a>
						&nbsp;
						<button onclick={() => navigator.clipboard.writeText(clipLink(clip.clip_id))} style="font-size: 0.75rem;">copy</button>
						</div>
					{:else if clip.status === 'failed'}
						<div style="color: red; font-size: 0.875rem;">failed</div>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
{/if}
