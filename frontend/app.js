import * as THREE from 'https://unpkg.com/three@0.154.0/build/three.module.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.154.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://unpkg.com/three@0.154.0/examples/jsm/controls/OrbitControls.js';
import { VRMLoaderPlugin } from 'https://unpkg.com/@pixiv/three-vrm@2.0.0/lib/three-vrm.module.js';

const canvas = document.getElementById('three-canvas');
if (canvas) {
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(35, window.innerWidth / window.innerHeight, 0.1, 20);
    // Position camera further back to see more of the body
    camera.position.set(0, 1.4, 4.0);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.3, 0);
    controls.update();

    const light = new THREE.DirectionalLight(0xffffff, Math.PI);
    light.position.set(1, 1, 1).normalize();
    scene.add(light);
    
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    const assetBase = window.location.pathname.includes('/frontend/') ? '../' : './';
    const vrml = `${assetBase}Character/OG/sakura_.vrm`;

    loader.load(
        vrml,
        (gltf) => {
            const vrm = gltf.userData.vrm;
            scene.add(vrm.scene);
            vrm.scene.rotation.y = Math.PI;
            window.waifuModel3D = vrm;
        },
        (progress) => {
            console.log('Sedang memuat model 3D...', 100.0 * (progress.loaded / progress.total), '%');
        },
        (error) => {
            console.error('Gagal memuat file VRM:', error);
        }
    );

    const clock = new THREE.Clock();
    function animate() {
        requestAnimationFrame(animate);
        const deltaTime = clock.getDelta();
        if (window.waifuModel3D) {
            window.waifuModel3D.update(deltaTime);
        }
        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}