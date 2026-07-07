import { HomeIcon } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-24">
      <h1 className="animate-pulse bg-linear-to-r from-foreground/80 to-muted-foreground bg-clip-text text-4xl font-bold text-transparent">
        Dashboard - Inzite V2
      </h1>
      <Link href="http://localhost:3000/">
        <button className="flex items-center mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600">
          <HomeIcon className="mr-2 w-5 h-5"/> Home
        </button>
      </Link>
    </div>
  );
}
