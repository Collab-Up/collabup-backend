// Script to automatically fix and update Firestore data for CollabUp
// - Ensures all faculty users have required fields
// - Ensures all researchProjects have valid facultyId
// - Updates mismatched or missing data

import admin from 'firebase-admin';
import { getFirestore } from 'firebase-admin/firestore';

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.applicationDefault(),
  });
}
const db = getFirestore();

async function fixFacultyUsers() {
  const usersRef = db.collection('users');
  const snapshot = await usersRef.where('role', '==', 'faculty').get();
  let updated = 0;
  for (const doc of snapshot.docs) {
    const data = doc.data();
    let needsUpdate = false;
    const update = {};
    if (!data.fullName) { update.fullName = 'Faculty ' + doc.id.slice(-4); needsUpdate = true; }
    if (!data.email) { update.email = `faculty${doc.id.slice(-4)}@example.com`; needsUpdate = true; }
    if (!data.instituteName) { update.instituteName = 'Unknown Institute'; needsUpdate = true; }
    if (data.role !== 'faculty') { update.role = 'faculty'; needsUpdate = true; }
    if (needsUpdate) {
      await usersRef.doc(doc.id).update(update);
      updated++;
      console.log(`Updated faculty user ${doc.id}:`, update);
    }
  }
  console.log(`Faculty users checked. ${updated} updated.`);
}

async function fixResearchProjects() {
  const usersRef = db.collection('users');
  const facultySnapshot = await usersRef.where('role', '==', 'faculty').get();
  const facultyIds = facultySnapshot.docs.map(doc => doc.id);
  const projectsRef = db.collection('researchProjects');
  const projectsSnapshot = await projectsRef.get();
  let updated = 0;
  for (const doc of projectsSnapshot.docs) {
    const data = doc.data();
    let needsUpdate = false;
    const update = {};
    // If facultyId is missing or invalid, assign a random valid facultyId
    if (!data.facultyId || !facultyIds.includes(data.facultyId)) {
      update.facultyId = facultyIds[Math.floor(Math.random() * facultyIds.length)];
      needsUpdate = true;
    }
    if (needsUpdate) {
      await projectsRef.doc(doc.id).update(update);
      updated++;
      console.log(`Updated researchProject ${doc.id}:`, update);
    }
  }
  console.log(`Research projects checked. ${updated} updated.`);
}

async function main() {
  await fixFacultyUsers();
  await fixResearchProjects();
  console.log('Firestore data fix complete.');
  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(1); });
