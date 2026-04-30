<script lang="ts">
	import { USERS } from '$lib/config';
	import { userStore } from '$lib/userStore.svelte';

	export const prerender = false;
	export const ssr = false;

	let { children } = $props();

	function handleUserChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		userStore.set(target.value);
	}
</script>

<nav>
    <a href="/">miniclip2</a>
    <a href="/uploads">uploads</a>
    <span style="flex: 1"></span>
    <label>
        user:
        <select
            value={userStore.current}
            onchange={handleUserChange}
        >
            {#each USERS as u}
                <option value={u}>{u}</option>
            {/each}
        </select>
    </label>
</nav>

<main>
    {@render children()}
</main>

<style>
    nav {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.5rem 1rem;
        border-bottom: 1px solid #ccc;
    }

    main {
        padding: 1rem;
    }
</style>
