"use client"

import { signOut } from "../lib/auth-client"


const SignOutButton =  () => {
    return (
        <button onClick={() => signOut()}>
            Signout
        </button>
    )
}
export default SignOutButton