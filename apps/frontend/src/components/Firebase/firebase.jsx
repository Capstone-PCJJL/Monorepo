import {initializeApp} from 'firebase/app';

import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  updatePassword,
  signInWithPopup,
  GoogleAuthProvider
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

const app = initializeApp(firebaseConfig);

class Firebase {
  constructor() {
    this.auth = getAuth(app);
    this.googleProvider = new GoogleAuthProvider();
  }
  
  doCreateUserWithEmailAndPassword = async (email, password) => {
    const userCredential = await createUserWithEmailAndPassword(this.auth, email, password);
    if (userCredential.user) {
      const userId = userCredential.user.uid;
      try {
        await fetch('/api/v1/users/firebase', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ firebase_id: userId }),
        });
      } catch (error) {
        console.error('Failed to create user in SQL database', error);
      }
    }
    return userCredential;
  };

  doSignInWithEmailAndPassword = (email, password) =>
    signInWithEmailAndPassword(this.auth, email, password);

  doSignOut = () => signOut(this.auth);

  doPasswordReset = email => sendPasswordResetEmail(this.auth, email);

  doPasswordUpdate = password =>
    updatePassword(this.auth.currentUser, password);

  doGetIdToken = () => {
    return new Promise((resolve, reject) => {
      const user = this.auth.currentUser;
      if (user) {
        user
          .getIdToken()
          .then(token => {
            resolve(token);
          })
          .catch(error => {
            reject(error);
          });
      } else {
        reject(new Error('No user is signed in.'));
      }
    });
  };


 /* Current logic always sends the UID to the backend, even if the user already exists.
  Within server.js check if the user already exists. If they do, do not send the UID to the backend.
  CheckUserSql is the query to check if the user already exists.*/
  doSignInWithGoogle = async () => {
    const userCredential = await signInWithPopup(this.auth, this.googleProvider);
    if (userCredential.user) {
      const { uid } = userCredential.user;
      console.log('Sending UID to backend:', uid);
      try {
        await fetch('/api/v1/users/firebase', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ firebase_id: uid }),
        });
      } catch (error) {
        console.error('Failed to create user in SQL database', error);
      }
    }
    return userCredential;
  };
}

export default Firebase;