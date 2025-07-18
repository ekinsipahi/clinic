export default class Slider {
  currSlide = 0;

  constructor({
    sliderContainer: selector,
    animateProps,
    initalSlide = 0,
    duration = 200,
    easing = "linear",
    infinite = false,
    touchControls = false,
    snapThreshold = 0.4
  }) {
    this.selector = selector;

    this.animateProps = animateProps;
    this.animationOpts = { duration, easing };

    this.isInfinite = infinite;

    this._initalSlide = initalSlide;

    this._touchControls = touchControls;
    this.snapThreshold = snapThreshold;
  }

  get sliderContainer() {
    return document.querySelector(this.selector);
  }
  get slides() {
    return Array.from(
      this.slideWrapper.querySelectorAll(".slide-wrapper .slide")
    );
  }
  get slideWrapper() {
    return this.sliderContainer.querySelector(".slide-wrapper");
  }
  get slideWidth() {
    return this.slides[0].offsetWidth;
  }
  get wrapperWidth() {
    return this.slideWrapper.offsetWidth;
  }

  init() {
    this.onInit?.();
    window.addEventListener("resize", () => this.moveSlide(this.currSlide));

    this.moveSlide(this._initalSlide, false);
    if (this._touchControls) this.initTouchControls();
  }

  isWithinBounds(index) {
    if (this.isInfinite) return true;
    return index >= 0 && index < this.slides.length;
  }

  computeAnimateProps(targetSlide, slideIndex, slideElem, progress = 1) {
    const props = {};
    for (let key of Object.keys(this.animateProps)) {
      props[key] = this.animateProps[key]({
        currSlide: targetSlide,
        prevSlide: this.currSlide,
        currDistance: Math.abs(slideIndex - targetSlide),
        prevDistance: Math.abs(slideIndex - this.currSlide),
        slideElem,
        slides: this.slides,
        slideIndex,
        progress,
        slideWidth: this.slideWidth,
        wrapperWidth: this.wrapperWidth
      });
    }
    return props;
  }

  moveSlide(targetSlide, animate = true) {
    if (!this.isWithinBounds(targetSlide))
      return this.moveSlide(this.currSlide);

    this.slides.forEach((slide, index) => {
      const props = this.computeAnimateProps(targetSlide, index, slide);
      if (animate) {
        const anim = slide.animate(props, this.animationOpts);
        anim.finished.then(() => Object.assign(slide.style, props));
      } else {
        Object.assign(slide.style, props);
      }
    });

    this.currSlide = targetSlide;
    this.onChange?.();
  }

  nextSlide() {
    this.moveSlide(this.currSlide + 1);
    this.onNext?.();
  }

  prevSlide() {
    this.moveSlide(this.currSlide - 1);
    this.onPrev?.();
  }

  initTouchControls() {
    this.slideWrapper.style.cursor = "grab";
    this.slideWrapper.addEventListener("dragstart", (e) => {
      e.preventDefault();
    });

    let originX,
      raf = null;

    const getDragVals = (e) => {
      const currX = e.touches?.[0]?.clientX ?? e.clientX;
      const deltaX = currX - originX;
      return {
        currX,
        deltaX,
        progress: deltaX / this.slideWidth,
        dir: -Math.sign(deltaX)
      };
    };
    const handleMouseDown = (e) => {
      e.preventDefault();
      if (e.type === "mousedown" && e.button !== 0) return;

      this.slideWrapper.style.cursor = "grabbing";

      originX = getDragVals(e).currX;

      this.startSlide = this.currSlide;
      this.onDragStart?.();
      bindMoveListeners(true);
    };

    const handleMouseMove = (e) => {
      e.preventDefault();

      if (raf) cancelAnimationFrame(raf);

      raf = requestAnimationFrame(() => {
        const { currX, progress, dir } = getDragVals(e);

        const target = this.currSlide + dir;

        this.slides.forEach((slide, i) => {
          const props = this.computeAnimateProps(
            target,
            i,
            slide,
            Math.abs(progress)
          );
          Object.assign(slide.style, props);
        });

        if (Math.abs(progress) >= 1) {
          this.currSlide += Math.floor(Math.abs(progress)) * dir;
          originX = currX;
        }

        this.onDrag?.();
      });
    };

    const handleMouseUp = (e) => {
      e.preventDefault();

      if (raf) cancelAnimationFrame(raf);
      this.slideWrapper.style.cursor = "grab";
      const { progress, dir } = getDragVals(e);

      const shouldSnap = Math.abs(progress) > this.snapThreshold;
      const target = shouldSnap ? this.currSlide + dir : this.currSlide;
      this.moveSlide(target);
      this.onDragEnd?.();

      bindMoveListeners(false);
    };

    const bindMoveListeners = (enable) => {
      const events = [
        ["touchmove", handleMouseMove, { passive: false }],
        ["mousemove", handleMouseMove],
        ["touchend", handleMouseUp],
        ["mouseup", handleMouseUp],
        ["mouseleave", handleMouseUp],
        ["touchcancel", handleMouseUp]
      ];

      events.forEach(([type, handler, options]) =>
        document[enable ? "addEventListener" : "removeEventListener"](
          type,
          handler,
          options
        )
      );
    };

    this.slideWrapper.addEventListener("mousedown", handleMouseDown);
    this.slideWrapper.addEventListener("touchstart", handleMouseDown, {
      passive: true
    });
  }
}

const minScale = 0;
const scaleFactor = 1;
const spacingFactor = 0.9;
const sliderWrapper = document.querySelector(".slide-wrapper");

const captions = [
  "Whispers of morning light",
  "Where the sky meets solitude",
  "Stories written in shadows",
  "The stillness of motion",
  "Geometry of the everyday",
  "Echoes of a passing moment",
  "Light and silence in balance",
  "A view from nowhere",
  "Color spills across time",
  "In the frame of imagination"
];

const lerp = (start, end, t) => start + t * (end - start);
const getScale = (distance, slidesLen) =>
  Math.pow(1 - (distance / slidesLen) * (1 - minScale), scaleFactor);
const getRotate = (slideIndex, currSlide) => (currSlide - slideIndex) * 60;
const getLeft = (slideIndex, currSlide, slideWidth, wrapperWidth) =>
  (slideIndex - currSlide) * slideWidth * spacingFactor +
  (wrapperWidth - slideWidth) / 2;

const slider = new Slider({
  sliderContainer: ".my-slider",
  touchControls: true,
  duration: 300,
  easing: "ease",

  animateProps: {
    transform({ prevSlide, slideIndex, currSlide, progress, slides }) {
      const fromScale = getRotate(slideIndex, prevSlide, slides.length);
      const toScale = getRotate(slideIndex, currSlide, slides.length);
      return `rotateY(${lerp(fromScale, toScale, progress)}deg)`;
    },
    scale({ currDistance, prevDistance, progress, slides }) {
      const fromScale = getScale(prevDistance, slides.length);
      const toScale = getScale(currDistance, slides.length);
      return lerp(fromScale, toScale, progress);
    },

    left({
      currSlide,
      prevSlide,
      slideIndex,
      progress,
      slideWidth,
      wrapperWidth
    }) {
      const fromLeft = getLeft(slideIndex, prevSlide, slideWidth, wrapperWidth);
      const toLeft = getLeft(slideIndex, currSlide, slideWidth, wrapperWidth);
      return `${lerp(fromLeft, toLeft, progress)}px`;
    }
    // zIndex: ({ currDistance }) => 100 - currDistance,
  }
});

function renderSlides(captions) {
  captions.forEach((caption, index) => {
    const slide = document.createElement("div");
    slide.className = "slide";
    slide.dataset.caption = caption;

    const img = document.createElement("img");
    img.src = `https://picsum.photos/300/400?random=${index + 1}`;
    img.loading = "lazy";
    img.alt = "";

    slide.appendChild(img);
    sliderWrapper.appendChild(slide);
  });
}

renderSlides(captions);

slider.onInit = () => {
  // Initalize Pagination
  slider.slides.forEach(() => {
    const bullet = document.createElement("div");
    bullet.className = "bullet";
    slider.sliderContainer.querySelector(".pagination").appendChild(bullet);
  });

  // Initialize Buttons
  document.querySelector(".btn-group .next-btn").onclick = () =>
    slider.nextSlide();
  document.querySelector(".btn-group .prev-btn").onclick = () =>
    slider.prevSlide();
};

slider.onChange = () => {
  // Update Captions
  slider.sliderContainer.querySelector(".captions").innerText =
    captions[slider.currSlide];
  // Update Pagination
  const bullets = slider.sliderContainer.querySelectorAll(
    ".pagination .bullet"
  );
  bullets?.forEach((b) => b.classList.remove("active"));
  bullets[slider.currSlide]?.classList.add("active");
};

slider.init();
