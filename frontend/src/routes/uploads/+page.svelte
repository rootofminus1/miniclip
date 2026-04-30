<script lang="ts">
	import { onMount } from 'svelte';
	import { listUploads, presignView } from '$lib/api';
	import { userStore } from '$lib/userStore.svelte';

	type Upload = {
		upload_id: string;
		s3_key: string;
		filename: string;
		created_at: string;
		status: string;
		thumbnail_ready: boolean;
		thumbnail_key?: string;

		thumbnail_url?: string;
	};

	let uploads = $state<Upload[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const data = await listUploads();

			const sorted = data.sort(
				(a: Upload, b: Upload) =>
					new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			);

			uploads = await Promise.all(
				sorted.map(async (u: Upload) => {
					if (u.thumbnail_ready && u.thumbnail_key) {
						return {
							...u,
							thumbnail_url: await presignView(u.thumbnail_key)
						};
					}
					return u;
				})
			);
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	onMount(load);

	$effect(() => {
		userStore.current;
		load();
	});
</script>

<h2>Uploads</h2>

{#if loading}
	<p>Loading...</p>
{:else if error}
	<p style="color: red">Error: {error}</p>
{:else if uploads.length === 0}
	<p>No uploads yet. The background recorder will upload replays automatically.</p>
{:else}
	<ul style="list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.75rem;">
		{#each uploads as upload}
			{@const href = `/uploads/${upload.upload_id}?key=${encodeURIComponent(upload.s3_key)}&filename=${encodeURIComponent(upload.filename ?? upload.upload_id)}`}
			
			<li>
				<a {href} style="display: flex; align-items: center; gap: 1rem; text-decoration: none; color: inherit;">

					{#if upload.thumbnail_url}
						<img
							src={upload.thumbnail_url}
							alt="thumbnail"
							style="width: 120px; height: 68px; object-fit: cover; flex-shrink: 0;"
						/>
					{:else}
						<div style="width: 120px; height: 68px; background: #ccc; flex-shrink: 0;"></div>
					{/if}

					<div>
						<div><strong>{upload.filename ?? upload.upload_id}</strong></div>
						<div style="font-size: 0.875rem; color: #555;">
							{new Date(upload.created_at).toLocaleString()}
						</div>
					</div>

				</a>
			</li>
		{/each}
	</ul>
{/if}