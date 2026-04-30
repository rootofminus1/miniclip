import { browser } from '$app/environment';
import { USERS } from './config';

type UserStore = {
	current: string;
	set: (u: string) => void;
};

function createUserStore(): UserStore {
	let user: string = $state(
		browser
			? (localStorage.getItem('miniclip2_user') ?? USERS[0])
			: USERS[0]
	);

	return {
		get current() {
			return user;
		},
		set(newUser: string) {
			user = newUser;
			if (browser) {
				localStorage.setItem('miniclip2_user', newUser);
			}
		}
	};
}

export const userStore = createUserStore();