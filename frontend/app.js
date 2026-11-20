import * as THREE from 'https://unpkg.com/three@0.154.0/build/three.module.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.154.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://unpkg.com/three@0.154.0/examples/jsm/controls/OrbitControls.js';
import { VRMLoaderPlugin, VRMUtils } from 'https://unpkg.com/@pixiv/three-vrm@2.0.0/lib/three-vrm.module.js';

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
            // VRM 0.x menghadap -Z, VRM 1.0 (sakura_.vrm) sudah menghadap kamera.
            // Dulu selalu diputar 180°, akibatnya Sakura membelakangi kamera.
            VRMUtils.rotateVRM0(vrm);
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

    // Di HP panel chat menutupi bagian bawah layar. Gambar digeser ke atas
    // dengan setViewOffset supaya Sakura berada di tengah ruang di atas panel.
    function layout3D() {
        // clientWidth/clientHeight, bukan innerWidth: lihat window.viewportSize di index.html
        const w = document.documentElement.clientWidth;
        const h = document.documentElement.clientHeight;
        const sheet = window.chatSheetHeight ? window.chatSheetHeight() : 0;
        const mobile = window.isMobileLayout ? window.isMobileLayout() : false;

        // Layar potret sempit: kamera mundur dan membidik tengah badan (±0,9 m),
        // supaya seluruh tubuh Sakura muat di ruang di atas panel chat.
        // Desktop tetap seperti dulu (jarak 4 m, membidik dada 1,3 m).
        const aim = mobile ? 0.9 : 1.3;
        camera.position.set(0, mobile ? 1.0 : 1.4, mobile ? 5.8 : 4.0);
        controls.target.set(0, aim, 0);
        controls.update();
        // aspek = ukuran gambar virtual penuh (w x (h + sheet)), supaya tidak gepeng
        camera.aspect = w / (h + sheet);
        if (sheet > 0) {
            camera.setViewOffset(w, h + sheet, 0, sheet, w, h);
        } else {
            camera.clearViewOffset();
        }
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }

    layout3D();
    window.addEventListener('resize', layout3D);
    if (window.onRelayout) window.onRelayout(layout3D);
}